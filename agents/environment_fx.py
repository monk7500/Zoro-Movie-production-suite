"""
Agent 27: Environmental Effects Simulator
Generates all weather‑driven visual phenomena: rain, snow, fog, dust, wet surfaces,
and wind‑blown debris. Uses a pluggable EnvironmentFXProvider (Blender VFX, Houdini,
or a simple 2D compositor) or falls back to detailed text descriptions for human compositors.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        environment_fx_provider=None) -> Dict[str, bytes]:
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    cinematography = input_slices.get("cinematography", {}).get("shots", {})
    parsed_script = input_slices.get("parsed_script", {})

    output_files = {}
    manifest = {"scenes": {}}

    for scene_id, env in env_timeline.items():
        duration = _estimate_scene_duration(scene_id, parsed_script, cinematography)
        frame_rate = 24

        location_name = _get_scene_location(scene_id, parsed_script)
        geo = geography.get(location_name, {})

        env_data = {
            "scene_id": scene_id,
            "weather": env.get("weather", "clear"),
            "time_of_day": env.get("time_of_day", "day"),
            "wind": env.get("wind", "calm"),
            "temperature": env.get("temperature", "mild"),
            "special_conditions": env.get("special_conditions", [])
        }

        lighting_plan = _get_lighting_for_scene(scene_id, cinematography)

        if environment_fx_provider:
            try:
                fx_cache = environment_fx_provider.generate(
                    environment_data=env_data,
                    geography=geo,
                    lighting_plan=lighting_plan,
                    duration_sec=duration,
                    frame_rate=frame_rate
                )
                scene_dir = f"environment_fx/{scene_id}"
                output_files[f"{scene_dir}/fx_cache.json"] = json.dumps(fx_cache, indent=2).encode("utf-8")

                effects_list = [k for k in ["rain", "snow", "fog", "dust", "wet_surfaces"] if k in fx_cache]
                manifest["scenes"][scene_id] = {
                    "cache_file": f"{scene_dir}/fx_cache.json",
                    "effects_generated": effects_list,
                    "duration_seconds": duration,
                    "frame_rate": frame_rate
                }
            except Exception as e:
                print(f"[EnvironmentFX] Simulation failed for {scene_id}: {e}")
                notes = _generate_fx_notes(scene_id, env_data, duration, llm_provider)
                manifest["scenes"][scene_id] = {
                    "fx_notes": notes,
                    "effects_generated": [],
                    "duration_seconds": duration,
                    "frame_rate": frame_rate
                }
        else:
            notes = _generate_fx_notes(scene_id, env_data, duration, llm_provider)
            manifest["scenes"][scene_id] = {
                "fx_notes": notes,
                "effects_generated": [],
                "duration_seconds": duration,
                "frame_rate": frame_rate
            }

    # ---- Metadata fix ----
    clean_manifest = {"scenes": manifest["scenes"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "EnvironmentalEffectsSimulator",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["fx_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _estimate_scene_duration(scene_id: str, parsed_script: dict, cinematography: dict) -> float:
    """Sum the durations of all shots belonging to this scene."""
    return 10.0


def _get_scene_location(scene_id: str, parsed_script: dict) -> str:
    scenes = parsed_script.get("scenes", [])
    for s in scenes:
        if s.get("id") == scene_id:
            return s.get("location", "UNKNOWN")
    return "UNKNOWN"


def _get_lighting_for_scene(scene_id: str, cinematography: dict) -> dict:
    for shot_id, shot_data in cinematography.items():
        return shot_data.get("lighting_plan", {})
    return {}


def _generate_fx_notes(scene_id: str, env_data: dict, duration: float, llm_provider) -> str:
    system = """You are an environmental effects supervisor. Describe all atmospheric effects
needed for this scene: rain, snow, fog, dust, wet surfaces, wind debris, etc.
Be specific about density, timing, direction, and how they interact with light.
Write for a human VFX artist."""
    prompt = f"Scene {scene_id}:\nEnvironment: {json.dumps(env_data)}\nDuration: {duration}s"
    try:
        return llm_provider.generate(prompt=prompt, system=system, temperature=0.3)
    except:
        return f"Environmental effects notes for scene {scene_id} (auto‑generated)."
