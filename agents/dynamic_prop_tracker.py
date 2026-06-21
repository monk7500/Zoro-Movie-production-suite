"""
Agent 30: Dynamic Prop Tracker Agent
Maintains a continuous state timeline for every dynamic prop.
Processes action lines via LLM to extract prop interactions (pick up, drop, break, etc.)
and updates position, condition, owner, and visibility per scene.
Outputs a per‑prop log that the Prop Continuity Validator uses.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    prop_states = input_slices.get("prop_classification", {}).get("props", {})
    parsed_script = input_slices.get("parsed_script", {})
    layout = input_slices.get("layout", {}).get("shots", {})
    wardrobe = input_slices.get("wardrobe_timeline", {}).get("characters", {})

    scenes = parsed_script.get("scenes", [])

    # ---- 1. Initialize state log from prop classification ----
    prop_log = {}
    for prop_name, prop_data in prop_states.items():
        if prop_data.get("classification") != "dynamic":
            continue
        init = prop_data.get("initial_state", {})
        prop_log[prop_name] = {
            "initial_state": {
                "position": init.get("position", {"x": 0, "y": 0, "z": 0}),
                "condition": init.get("condition", "unknown"),
                "owner": init.get("owner", None),
                "visibility": init.get("visibility", True)
            },
            "timeline": []
        }

    if not prop_log:
        empty = {"props": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "DynamicPropTracker",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"prop_tracker_log.json": final_json.encode("utf-8")}

    # ---- 2. Extract prop events from action lines (LLM, per scene) ----
    for scene in scenes:
        sid = scene["id"]
        actions = scene.get("action_lines", [])
        if not actions:
            continue

        events = _extract_prop_events(sid, actions, list(prop_log.keys()), llm_provider)

        # Apply events in sequence, updating the state
        for event in events:
            pname = event.get("prop")
            if pname not in prop_log:
                continue

            # Current state = last timeline entry, or initial if no events yet
            if prop_log[pname]["timeline"]:
                current = prop_log[pname]["timeline"][-1]["new_state"].copy()
            else:
                current = prop_log[pname]["initial_state"].copy()

            new_state = _apply_event(current, event)
            prop_log[pname]["timeline"].append({
                "scene": sid,
                "event": event.get("event", "unknown"),
                "timecode_seconds": event.get("timecode_seconds", 0.0),
                "new_state": new_state
            })

    # ---- 3. Add metadata ----
    result = {"props": prop_log}
    clean_data = {"props": result["props"]}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    result["_meta"] = {
        "agent": "DynamicPropTracker",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(result, indent=2, ensure_ascii=False)
    return {"prop_tracker_log.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _extract_prop_events(scene_id: str, actions: List[str], prop_names: List[str], llm_provider) -> List[dict]:
    """Use LLM to find all interactions with known dynamic props."""
    if not actions or not prop_names:
        return []

    system = f"""You are a continuity tracker. The known dynamic props are: {', '.join(prop_names)}.
Analyze these action lines and list every interaction with these props.
Output a JSON array of events with:
- "prop": the prop name (must match one of the known props exactly)
- "event": "picked_up", "dropped", "placed", "thrown", "broken", "opened", "closed", "filled", "emptied", "consumed"
- "character": the character performing the action (if clear)
- "timecode_seconds": estimated time from scene start (0.0 if unknown)

Only include props from the list. If no props are interacted with, output [].
Output ONLY a valid JSON array."""

    try:
        response = llm_provider.generate(
            prompt=f"Scene {scene_id} actions:\n" + "\n".join(actions),
            system=system,
            temperature=0.1
        )
        return _extract_json_array(response)
    except:
        return []


def _apply_event(current_state: dict, event: dict) -> dict:
    """Apply a single event to the prop's state, returning the new state."""
    new = current_state.copy()
    event_type = event.get("event", "")
    character = event.get("character")

    if event_type == "picked_up":
        new["owner"] = character
        new["position"]["z"] = new.get("position", {}).get("z", 0) + 1.0  # approximate hand height
    elif event_type == "dropped":
        new["owner"] = None
        new["position"]["z"] = 0.0  # on floor
    elif event_type == "placed":
        new["owner"] = None
    elif event_type == "broken":
        new["condition"] = "broken"
    elif event_type == "opened":
        new["condition"] = "open"
    elif event_type == "closed":
        new["condition"] = "closed"
    elif event_type == "filled":
        new["condition"] = "full"
    elif event_type == "emptied":
        new["condition"] = "empty"
    elif event_type == "consumed":
        new["condition"] = "consumed"
        new["visibility"] = False  # eaten/drunk, gone

    return new


def _extract_json_array(response: str) -> List[dict]:
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "events" in data:
            return data["events"]
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[[\s\S]*\]', response)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return []
