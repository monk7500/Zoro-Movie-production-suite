"""
Agent 20: Ambience & Soundscape Agent
Generates continuous ambient background audio for every scene:
room tone, weather, environmental sounds, and location‑specific atmosphere.
Uses a pluggable AudioFXProvider or falls back to text descriptions.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        fx_provider=None) -> Dict[str, bytes]:
    """
    Args:
        input_slices: {
            "environment_timeline": environment_timeline.scenes,
            "location_profiles": location_profiles.locations,
            "parsed_script": parsed_script   (for scene→location mapping)
        }
        bible_version: current Bible version string
        llm_provider: instance of LLMProvider (unused here but kept for interface consistency)
        fx_provider: optional instance of AudioFXProvider
    Returns:
        Output files: ambience/{scene_id}_ambience.wav + ambience_manifest.json
    """
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})
    locations = input_slices.get("location_profiles", {}).get("locations", {})
    parsed_script = input_slices.get("parsed_script", {})

    output_files = {}
    manifest = {"scenes": {}}

    for scene_id, env in env_timeline.items():
        # Determine the location for this scene
        location_name = _get_scene_location(scene_id, parsed_script)
        loc = locations.get(location_name, {})

        # Build a rich ambience description
        weather = env.get("weather", "clear")
        time_of_day = env.get("time_of_day", "day")
        wind = env.get("wind", "calm")
        temperature = env.get("temperature", "mild")
        specials = ", ".join(env.get("special_conditions", []))
        loc_desc = loc.get("description", location_name)
        loc_ambience = loc.get("ambience", "")

        description = (
            f"{time_of_day} {weather}, {wind} wind, {temperature}, "
            f"{loc_desc} {loc_ambience} {specials}"
        ).strip()
        description = " ".join(description.split())  # normalize whitespace

        # Generate ambience audio (or text placeholder)
        duration = 60.0  # seconds; looping can be done at assembly time

        if fx_provider:
            try:
                audio_bytes = fx_provider.generate(
                    description=description,
                    duration_seconds=duration,
                    environment=env
                )
                filename = f"ambience/{scene_id}_ambience.wav"
                output_files[filename] = audio_bytes
                manifest["scenes"][scene_id] = filename
            except Exception as e:
                print(f"[Ambience] AudioFX generation failed for {scene_id}: {e}")
                manifest["scenes"][scene_id] = f"[AUDIO UNAVAILABLE] {description}"
        else:
            # No provider — text description
            manifest["scenes"][scene_id] = description

    # ---- Metadata fix ----
    clean_manifest = {"scenes": manifest["scenes"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "AmbienceSoundscapeAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["ambience_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _get_scene_location(scene_id: str, parsed_script: dict) -> str:
    """Look up the location name from the parsed script."""
    scenes = parsed_script.get("scenes", [])
    for scene in scenes:
        if scene.get("id") == scene_id:
            return scene.get("location", "UNKNOWN")
    return "UNKNOWN"
