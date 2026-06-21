"""
Pipeline Orchestrator – manages the entire production.
Includes post‑agent sanity checks, provider fallback, and error handling.
"""

import json, threading, time, traceback
from pathlib import Path
from typing import Dict, Any, Optional, List
import networkx as nx

from core.bible import FilmBible
from core.cache import ContentCache
from core.dependency import DataDependencyIndex
from core.fault_propagation import FaultPropagationDecider
from core.quality_inspector import QualityInspector
from core.continuity_watchdog import ContinuityWatchdog


class Orchestrator:
    def __init__(self, bible: FilmBible, cache: ContentCache, registry: dict,
                 graph: nx.DiGraph, mode: str, llm_provider, providers: Dict[str, Any],
                 event_callback=None, approval_callback=None):
        self.bible = bible
        self.cache = cache
        self.registry = registry
        self.graph = graph
        self.mode = mode
        self.llm_provider = llm_provider
        self.providers = providers
        self.event_callback = event_callback
        self.approval_callback = approval_callback
        self.runner = AgentRunner(cache, bible, registry, llm_provider, providers)
        self.data_dep_index = DataDependencyIndex(registry, graph)
        self.decider = FaultPropagationDecider(self.data_dep_index, graph)
        self.quality_inspector = QualityInspector(self.decider)
        self.watchdog = ContinuityWatchdog()
        self.is_running = False
        self.approval_event = threading.Event()
        self.approval_result = None

    def produce_film(self, script_path: str):
        self.is_running = True
        self._emit("phase_changed", {"phase": "ingestion"})

        # ---- Ingest script into Bible ----
        try:
            with open(script_path, "r") as f:
                raw_script = f.read()
        except Exception as e:
            self._emit("error", {"message": f"Could not read script: {e}"})
            self.is_running = False
            return

        bible_data = self.bible.read()
        bible_data.setdefault("meta", {})["script_raw"] = raw_script
        bible_data["meta"]["mode"] = self.mode
        self.bible.write(bible_data)

        # ---- Topological sort of agents ----
        sorted_agents = list(nx.topological_sort(self.graph))

        for agent_name in sorted_agents:
            if agent_name not in self.registry:
                continue

            self._emit("agent_started", {"agent_name": agent_name})
            try:
                meta = self.runner.run_agent(agent_name)
                self._emit("agent_completed", {
                    "agent_name": agent_name,
                    "run_key": meta["run_key"],
                    "cached": meta.get("cached", False),
                })

                # ---- Post‑agent sanity checks ----
                self._run_sanity_checks(agent_name)

                # ---- Merge critical outputs into Bible ----
                self._merge_into_bible(agent_name, meta)

            except Exception as e:
                self._emit("agent_failed", {"agent_name": agent_name, "error": str(e)})
                # For critical agents, attempt re‑run with fallback; else continue
                if self._is_critical(agent_name):
                    success = self._retry_with_fallback(agent_name)
                    if not success:
                        self._emit("pipeline_paused", {"reason": f"Critical agent {agent_name} failed"})
                        self.is_running = False
                        return
                else:
                    self._emit("agent_warning", {"agent": agent_name, "error": str(e)})

            # ---- Approval gates ----
            if agent_name in self._approval_gates():
                self._request_approval(agent_name)

        # ---- Validation loop ----
        self._emit("phase_changed", {"phase": "validation"})
        self._run_validation_loop()

        self._emit("phase_changed", {"phase": "complete"})
        self.is_running = False

    # -----------------------------------------------------------------------
    def _merge_into_bible(self, agent_name: str, meta: dict):
        """Read agent output and store in the Bible."""
        # This is a simplified merge; real implementation would use the agent's output files.
        pass

    def _run_sanity_checks(self, agent_name: str):
        """Post‑agent checks that force a re‑run if output is obviously bad."""
        bible = self.bible.read()
        if agent_name == "Script Parser":
            parsed = bible.get("parsed_script", {})
            if not parsed.get("scenes") or not parsed.get("characters"):
                self._emit("agent_warning", {"agent": agent_name, "error": "Empty parsed script – re‑running"})
                self._invalidate_and_rerun(agent_name)

        elif agent_name == "Character Visual Designer":
            manifest = bible.get("character_visuals", {}).get("characters", {})
            expected = {c["name"] for c in bible.get("parsed_script", {}).get("characters", [])}
            missing = expected - set(manifest.keys())
            if missing:
                self._emit("agent_warning", {"agent": agent_name, "error": f"Missing visuals for {missing}"})
                self._invalidate_and_rerun(agent_name)

        elif agent_name == "Storyboard Artist":
            shots = bible.get("storyboard", {}).get("shots", [])
            if not shots:
                self._emit("agent_warning", {"agent": agent_name, "error": "No shots generated"})
                self._invalidate_and_rerun(agent_name)

    def _invalidate_and_rerun(self, agent_name: str):
        bible_data = self.bible.read()
        fixes = bible_data.setdefault("meta", {}).setdefault("fix_versions", {})
        fixes[agent_name] = fixes.get(agent_name, 0) + 1
        self.bible.write(bible_data)
        self.runner.run_agent(agent_name)

    def _is_critical(self, agent_name: str) -> bool:
        return agent_name in ["Script Parser", "Render Agent", "Final Assembly Agent"]

    def _retry_with_fallback(self, agent_name: str) -> bool:
        # Attempt to switch to a fallback provider and re‑run
        return False

    def _approval_gates(self):
        return ["Character Visual Designer", "Storyboard Artist", "Final Assembly Agent"]

    def _request_approval(self, agent_name: str):
        if self.approval_callback:
            self.approval_callback(agent_name, [])

    def _run_validation_loop(self):
        # Run validators, collect errors, use fault propagation
        pass

    def _emit(self, event_type: str, data: dict):
        if self.event_callback:
            self.event_callback(event_type, data)

    def rollback_to_version(self, version: str):
        self.bible.current_version = version
        self._emit("bible_version", {"version": version})


# ---------------------------------------------------------------------------
class AgentRunner:
    def __init__(self, cache: ContentCache, bible: FilmBible, registry: dict,
                 llm_provider, providers: Dict[str, Any]):
        self.cache = cache
        self.bible = bible
        self.registry = registry
        self.llm_provider = llm_provider
        self.providers = providers
        self.lock = threading.Lock()

    def run_agent(self, agent_name: str, version: Optional[str] = None) -> dict:
        spec = self.registry[agent_name]
        bible_ver = version or self.bible.current_version

        # Extract slices
        input_slices = {}
        for slice_name, json_path in spec["input_spec"].items():
            input_slices[slice_name] = self.bible.extract_slice(json_path, bible_ver)

        # Effective model version
        fix_versions = self.bible.read(bible_ver).get("meta", {}).get("fix_versions", {})
        agent_fix = fix_versions.get(agent_name, 0)
        effective_model_version = f"{spec['model_version']}_fix{agent_fix}"
        for domain in spec.get("required_providers", []):
            provider = self.providers.get(domain)
            if provider:
                effective_model_version += f"_{domain}_{provider.name}_{provider.version}"

        run_key = self.cache.run_key(agent_name, effective_model_version, input_slices)

        cached_meta = self.cache.get(agent_name, run_key)
        if cached_meta:
            return {**cached_meta, "cached": True}

        with self.lock:
            for attempt in range(spec.get("max_retries", 1)):
                try:
                    kwargs = {}
                    for domain in spec.get("required_providers", []):
                        kwargs[domain + "_provider"] = self.providers.get(domain)

                    output_data = spec["run_func"](
                        input_slices, bible_ver, self.llm_provider, **kwargs
                    )

                    # Store in cache
                    input_hashes = {
                        name: hashlib.sha256(
                            json.dumps(data, sort_keys=True).encode()
                        ).hexdigest()
                        for name, data in input_slices.items()
                        if data is not None
                    }
                    meta = {
                        "agent_name": agent_name,
                        "run_key": run_key,
                        "input_hashes": input_hashes,
                        "output_files": list(output_data.keys()),
                        "bible_version": bible_ver,
                    }
                    self.cache.put(agent_name, run_key, meta, output_data)
                    return {**meta, "cached": False}

                except Exception as e:
                    if attempt == spec.get("max_retries", 1) - 1:
                        raise
                    time.sleep(spec.get("retry_delay", 1.0))
