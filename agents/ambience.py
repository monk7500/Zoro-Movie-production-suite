"""
Agent 20: Ambience & Soundscape – placeholder.
"""

import json

def run(input_slices, bible_version, llm_provider, fx_provider=None):
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})
    locations = input_slices.get("location_profiles", {}).get("locations", {})
    manifest = {"scenes": {}}

    for scene_id, env in env_timeline.items():
        manifest["scenes"][scene_id] = f"Ambience for {scene_id}: {env.get('weather', 'clear')}"

    return {"ambience_manifest.json": json.dumps(manifest).encode()}
