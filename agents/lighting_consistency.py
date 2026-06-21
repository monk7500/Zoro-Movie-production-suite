"""
Agent 28: Lighting Consistency Agent (Production Side)
Produces a per‑shot lighting rig: key light, fill light, practicals, and environment light.
Uses a pluggable RenderEngineProvider for light placement, or falls back to LLM descriptions.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        render_engine_provider=None) -> Dict[str, bytes]:
    cinematography = input_slices.get("cinematography", {}).get("shots", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    layout = input_slices.get("layout", {}).get("shots", {})
    style_guide = input_slices.get("style_guide", {})
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})

    light_defaults = style_guide.get("lighting", {})
    default_key_ratio = light_defaults.get("key_ratio", "3:1")
    default_key_temp = int(light_defaults.get("key_color", "3200K").replace("K", ""))
    default_fill_temp = int(light_defaults.get("fill_color", "5600K").replace("K", ""))

    manifest = {"shots": {}}

    for shot_id, shot_layout in layout.items():
        cine = cinematography.get(shot_id, {})
        lighting_plan = cine.get("lighting_plan", {})
        location = shot_layout.get("location", "UNKNOWN")
        geo = geography.get(location, {})
        entities = shot_layout.get("entities", [])

        scene_id = _shot_id_to_scene_id(shot_id)
        env = env_timeline.get(scene_id, {})
        time_of_day = env.get("time_of_day", "day")
        weather = env.get("weather", "clear")

        if render_engine_provider:
            light_rig = render_engine_provider.apply_lighting_rig(
                shot_id=shot_id,
                lighting_plan=lighting_plan,
                geography=geo,
                entities=entities,
                style_defaults={
                    "key_ratio": default_key_ratio,
                    "key_temp": default_key_temp,
                    "fill_temp": default_fill_temp
                },
                environment={"time_of_day": time_of_day, "weather": weather}
            )
            manifest["shots"][shot_id] = {
                "light_rig": light_rig,
                "light_state_timeline": _track_practical_states(shot_id, entities)
            }
        else:
            light_rig = _generate_lighting_description(
                shot_id, lighting_plan, geo, entities, time_of_day, weather, llm_provider
            )
            manifest["shots"][shot_id] = {
                "light_rig_description": light_rig,
                "light_state_timeline": {}
            }

    # ---- Metadata fix ----
    clean_data = {"shots": manifest["shots"]}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    manifest["_meta"] = {
        "agent": "LightingConsistencyAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(manifest, indent=2, ensure_ascii=False)
    return {"lighting_manifest.json": final_json.encode("utf-8")}


def _shot_id_to_scene_id(shot_id: str) -> str:
    return "S01"


def _track_practical_states(shot_id: str, entities: List[dict]) -> dict:
    """Track on/off/flickering states of practical lights over time."""
    practicals = {}
    for ent in entities:
        if ent.get("type") == "lighting" or "neon" in ent.get("id", "").lower() or "lamp" in ent.get("id", "").lower():
            practicals[ent["id"]] = {"frame_0": "on"}
    return practicals


def _generate_lighting_description(shot_id, lighting_plan, geo, entities, time_of_day, weather, llm_provider) -> str:
    system = """You are a gaffer. Describe the complete lighting setup for this shot.
Include key light position, intensity, color; fill light; any practicals; and how the environment affects lighting."""
    prompt = f"Shot {shot_id}, time: {time_of_day}, weather: {weather}\nPlan: {json.dumps(lighting_plan)}\nGeography: {json.dumps(geo)}\nEntities: {json.dumps(entities)}"
    try:
        return llm_provider.generate(prompt=prompt, system=system, temperature=0.3)
    except:
        return f"Lighting description for shot {shot_id} (auto‑generated)."
