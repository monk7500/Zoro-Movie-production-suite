"""
Agent 13: Prop Classifier – placeholder.
"""

import json

def run(input_slices, bible_version, llm_provider):
    prop_catalog = input_slices.get("prop_catalog", {}).get("props", {})
    classification = {"props": {}}
    for name, data in prop_catalog.items():
        classification["props"][name] = {
            "classification": data.get("classification", "dynamic"),
            "initial_state": {
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"y": 0},
                "condition": data.get("default_state", "unknown"),
                "visibility": True,
                "owner": None
            },
            "location": data.get("location_typical", "")
        }
    return {"prop_classification.json": json.dumps(classification).encode()}
