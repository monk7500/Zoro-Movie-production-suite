"""
Agent 12: Geography Definition Agent – placeholder.
"""

import json

def run(input_slices, bible_version, llm_provider):
    location_profiles = input_slices.get("location_profiles", {}).get("locations", {})
    prop_catalog = input_slices.get("prop_catalog", {}).get("props", {})
    geography = {"locations": {}}
    for loc_name in location_profiles:
        geography["locations"][loc_name] = {
            "boundary": {"type": "rectangle", "width_m": 5.0, "depth_m": 5.0, "height_m": 2.5},
            "fixed_objects": [],
            "entrances": [{"id": "main_door", "position": {"x": 0, "y": 2.5, "z": 0}, "width": 1.0, "type": "door"}]
        }
    return {"geography.json": json.dumps(geography).encode()}
