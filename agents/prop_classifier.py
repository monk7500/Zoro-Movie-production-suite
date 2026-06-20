"""
Agent 13: Prop Classifier Agent
Finalizes the classification (hard_fixed / dynamic) of every prop, and generates
an initial runtime state (position, condition, visibility, owner) for each dynamic prop.
Directly seeds the Dynamic Prop Tracker and the Prop Continuity Validator.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    prop_catalog = input_slices.get("prop_catalog", {}).get("props", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    parsed_script = input_slices.get("parsed_script", {})

    if not prop_catalog:
        empty = {"props": {}}
        return {"prop_classification.json": json.dumps(empty, indent=2).encode("utf-8")}

    # 1. Build a summary of each prop with tentative classification and context
    prop_summaries = _build_prop_summaries(prop_catalog, geography)

    # 2. LLM‑based classification refinement
    system_prompt = _build_system_prompt()
    user_prompt = f"Props:\n{prop_summaries}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=16384
        )
        classification = _extract_json(response)
    except Exception:
        classification = _fallback_classification(prop_catalog, geography)

    # 3. Validate and fill
    classification = _validate_and_fill(classification, prop_catalog, geography)

    # 4. Add metadata
    output_json = json.dumps(classification, indent=2, ensure_ascii=False)
    classification["_meta"] = {
        "agent": "PropClassifierAgent",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"prop_classification.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a continuity supervisor. Finalize the classification of each prop as "hard_fixed" (part of the set, never moves) or "dynamic" (can be moved/held/interacted with).

For each dynamic prop, provide an "initial_state" with:
- "position": { "x": float, "y": float, "z": float } – the world position when the prop first appears. Use geography data if listed; otherwise estimate.
- "rotation": { "y": float } – rotation around vertical axis in degrees.
- "condition": a short string (e.g., "clean", "half_full", "broken", "flickering").
- "visibility": true/false (usually true).
- "owner": (optional) the character who initially possesses it, or null.

For hard_fixed props, the initial_state can mirror the fixed object position from the geography. No owner, no movement.

Use the provided tentative classification and context. If a prop is furniture, structural, or a large fixture → hard_fixed. If handheld, wearable, or moved in script → dynamic.
Output ONLY valid JSON with top-level key "props"."""


def _build_prop_summaries(prop_catalog: dict, geography: dict) -> str:
    parts = []
    for prop_name, prop_data in prop_catalog.items():
        tentative_class = prop_data.get("classification", "dynamic")
        location = prop_data.get("location_typical", "unknown")
        context = prop_data.get("context", "")
        # Check if the prop is already placed in geography
        geo_fixed = False
        for loc_geo in geography.values():
            for obj in loc_geo.get("fixed_objects", []):
                if obj.get("id") == prop_name:
                    geo_fixed = True
                    break
            if geo_fixed:
                break
        parts.append(
            f"{prop_name}: tentative_class={tentative_class}, location={location}, "
            f"context='{context}', in_geography_fixed={geo_fixed}"
        )
    return "\n".join(parts)


def _extract_json(response: str) -> dict:
    try: return json.loads(response)
    except: pass
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if fence:
        try: return json.loads(fence.group(1))
        except: pass
    brace = re.search(r'\{[\s\S]*\}', response)
    if brace:
        try: return json.loads(brace.group(0))
        except: pass
    return {}


def _fallback_classification(prop_catalog: dict, geography: dict) -> dict:
    classification = {"props": {}}
    for prop_name, prop_data in prop_catalog.items():
        classif = prop_data.get("classification", "dynamic")
        position = {"x": 0.0, "y": 0.0, "z": 0.0}
        if classif == "hard_fixed":
            for loc_geo in geography.values():
                for obj in loc_geo.get("fixed_objects", []):
                    if obj.get("id") == prop_name:
                        position = obj.get("position", position)
                        break
        classification["props"][prop_name] = {
            "classification": classif,
            "initial_state": {
                "position": position,
                "rotation": {"y": 0.0},
                "condition": prop_data.get("default_state", "unknown"),
                "visibility": True,
                "owner": None
            },
            "location": prop_data.get("location_typical", "")
        }
    return classification


def _validate_and_fill(classification: dict, prop_catalog: dict, geography: dict) -> dict:
    classification.setdefault("props", {})
    for prop_name, prop_data in prop_catalog.items():
        if prop_name not in classification["props"]:
            classif = prop_data.get("classification", "dynamic")
            position = {"x": 0.0, "y": 0.0, "z": 0.0}
            if classif == "hard_fixed":
                for loc_geo in geography.values():
                    for obj in loc_geo.get("fixed_objects", []):
                        if obj.get("id") == prop_name:
                            position = obj.get("position", position)
                            break
            classification["props"][prop_name] = {
                "classification": classif,
                "initial_state": {
                    "position": position,
                    "rotation": {"y": 0.0},
                    "condition": prop_data.get("default_state", "unknown"),
                    "visibility": True,
                    "owner": None
                },
                "location": prop_data.get("location_typical", "")
            }
        else:
            entry = classification["props"][prop_name]
            entry.setdefault("classification", prop_data.get("classification", "dynamic"))
            entry.setdefault("location", prop_data.get("location_typical", ""))
            istate = entry.setdefault("initial_state", {})
            istate.setdefault("position", {"x": 0.0, "y": 0.0, "z": 0.0})
            istate.setdefault("rotation", {"y": 0.0})
            istate.setdefault("condition", prop_data.get("default_state", "unknown"))
            istate.setdefault("visibility", True)
            if "owner" not in istate:
                istate["owner"] = None
    return classification
