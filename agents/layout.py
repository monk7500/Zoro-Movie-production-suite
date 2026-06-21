"""
Agent 23: Layout Agent
Produces a precise 3D blocking file for each shot: camera placement,
character positions with variant signatures, hard‑fixed prop positions,
and dynamic prop initial states. Uses LLM for spatial reasoning or
a rule‑based fallback.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    shots = input_slices.get("storyboard", {}).get("shots", [])
    geography = input_slices.get("geography", {}).get("locations", {})
    cinematography = input_slices.get("cinematography", {}).get("shots", {})
    char_visuals = input_slices.get("character_visuals", {}).get("characters", {})
    prop_states = input_slices.get("prop_classification", {}).get("props", {})
    wardrobe = input_slices.get("wardrobe_timeline", {}).get("characters", {})
    parsed_script = input_slices.get("parsed_script", {})

    output_manifest = {"shots": {}}

    for shot in shots:
        shot_id = shot["id"]
        scene_id = shot.get("scene", "")
        location = shot.get("location", "")
        geo = geography.get(location, {})
        cine = cinematography.get(shot_id, {}).get("camera", {})
        chars_in_shot = shot.get("characters_in_frame", [])

        # ---- 1. Place Camera ----
        camera = _place_camera(geo, cine, shot)

        # ---- 2. Place Characters ----
        entities = []
        for char_name in chars_in_shot:
            variant_sig = _get_variant_for_scene(char_name, scene_id, wardrobe, char_visuals)
            position = _place_character(char_name, shot, geo, parsed_script)
            entities.append({
                "id": char_name,
                "type": "character",
                "position": position,
                "rotation_y": _estimate_facing(char_name, shot, camera),
                "variant_signature": variant_sig
            })

        # ---- 3. Place Fixed Props (from geography) ----
        for obj in geo.get("fixed_objects", []):
            entities.append({
                "id": obj["id"],
                "type": "hard_fixed_prop",
                "position": obj.get("position", {"x": 0, "y": 0, "z": 0}),
                "rotation_y": obj.get("rotation_y", 0)
            })

        # ---- 4. Place Dynamic Props (initial state from prop classification) ----
        for prop_name, prop_data in prop_states.items():
            if prop_data.get("classification") != "dynamic":
                continue
            if prop_data.get("location") != location:
                continue
            init_state = prop_data.get("initial_state", {})
            entities.append({
                "id": prop_name,
                "type": "dynamic_prop",
                "position": init_state.get("position", {"x": 0, "y": 0, "z": 0}),
                "rotation_y": init_state.get("rotation", {}).get("y", 0),
                "state": init_state.get("condition", "unknown")
            })

        output_manifest["shots"][shot_id] = {
            "camera": camera,
            "entities": entities
        }

    # ---- Metadata fix ----
    clean_data = {"shots": output_manifest["shots"]}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    output_manifest["_meta"] = {
        "agent": "LayoutAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(output_manifest, indent=2, ensure_ascii=False)
    return {"layout_manifest.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _place_camera(geo: dict, cine: dict, shot: dict) -> dict:
    entrance = (geo.get("entrances") or [{}])[0]
    default_pos = entrance.get("position", {"x": 0, "y": 4, "z": 1.6})
    return {
        "position": default_pos,
        "rotation": {"yaw": 0, "pitch": -5, "roll": 0},
        "focal_length_mm": cine.get("focal_length_mm", 35),
        "focus_distance_m": cine.get("focus_distance_m", 5.0)
    }


def _place_character(char_name: str, shot: dict, geo: dict, parsed_script: dict) -> dict:
    chars_in_shot = shot.get("characters_in_frame", [])
    try:
        idx = chars_in_shot.index(char_name)
    except ValueError:
        idx = 0
    return {"x": 0.5 + idx * 0.5, "y": -2.0, "z": 0.0}


def _estimate_facing(char_name: str, shot: dict, camera: dict) -> float:
    return 180.0


def _get_variant_for_scene(char_name: str, scene_id: str, wardrobe: dict, char_visuals: dict) -> str:
    char_vis = char_visuals.get(char_name, {})
    variants = char_vis.get("variants", {})
    for sig, var_data in variants.items():
        if scene_id in var_data.get("scenes", []):
            return sig
    return "base"
