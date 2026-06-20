"""
Agent 23: Layout Agent – placeholder.
"""

import json

def run(input_slices, bible_version, llm_provider):
    shots = input_slices.get("storyboard", {}).get("shots", [])
    geography = input_slices.get("geography", {}).get("locations", {})
    manifest = {"shots": {}}

    for shot in shots:
        sid = shot["id"]
        location = shot.get("location", "")
        geo = geography.get(location, {})
        entrance = (geo.get("entrances") or [{}])[0]
        cam_pos = entrance.get("position", {"x": 0, "y": 4, "z": 1.6})
        manifest["shots"][sid] = {
            "camera": {"position": cam_pos, "rotation": {"yaw": 0, "pitch": -5, "roll": 0}, "focal_length_mm": 35, "focus_distance_m": 5.0},
            "entities": []
        }
    return {"layout_manifest.json": json.dumps(manifest).encode()}
