"""
Pipeline Orchestrator – manages the entire production.
Simplified version for the repository skeleton.
"""

import json, threading, time
from pathlib import Path

class Orchestrator:
    def __init__(self, bible, cache, registry, graph, mode, llm_provider, providers,
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
        self.is_running = False

    def produce_film(self, script_path: str):
        self.is_running = True
        self._emit("phase_changed", {"phase": "ingestion"})
        # … full implementation will run all agents in topological order
        self._emit("phase_changed", {"phase": "complete"})
        self.is_running = False

    def _emit(self, event_type, data):
        if self.event_callback:
            self.event_callback(event_type, data)

    def rollback_to_version(self, version: str):
        self.bible.current_version = version
        self._emit("bible_version", {"version": version})
