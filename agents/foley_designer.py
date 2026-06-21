"""
Agent 19: Foley Designer Agent
Generates diegetic sound effects for every scene from action descriptions and prop states.
Outputs audio files (WAV) or text cue sheets with precise timings.
Uses a pluggable AudioFXProvider or falls back to text descriptions.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        fx_provider=None) -> Dict[str, bytes]:
    """
    Args:
        input_slices: {
            "parsed_script": parsed_script,
            "prop_classification": prop_classification.props,
            "environment_timeline": environment_timeline.scenes,
            "location_profiles": location_profiles.locations
        }
        bible_version: current Bible version string
        llm_provider: instance of LLMProvider
        fx_provider: optional instance of AudioFXProvider
    Returns:
        Output files: foley/{scene_id}/{sound_id}.wav + foley_manifest.json
    """
    parsed_script = input_slices.get("parsed_script", {})
    prop_states = input_slices.get("prop_classification", {}).get("props", {})
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})
    locations = input_slices.get("location_profiles", {}).get("locations", {})

    scenes = parsed_script.get("scenes", [])
    output_files = {}
    manifest = {"scenes": {}}

    for scene in scenes:
        sid = scene["id"]
        actions = scene.get("action_lines", [])
        env = env_timeline.get(sid, {})
        loc_name = scene.get("location", "")
        loc = locations.get(loc_name, {})

        # 1. Extract sound cues from action lines via LLM
        action_text = " ".join(actions)
        sound_cues = _extract_sound_cues(action_text, llm_provider, env, loc)

        scene_sounds = []
        for cue in sound_cues:
            description = cue.get("description", "")
            duration = cue.get("duration_seconds", 2.0)

            if fx_provider:
                try:
                    audio_bytes = fx_provider.generate(
                        description=description,
                        duration_seconds=duration,
                        environment=env
                    )
                    sound_id = f"foley_{sid}_{description.replace(' ', '_')[:40]}"
                    filename = f"foley/{sid}/{sound_id}.wav"
                    output_files[filename] = audio_bytes
                    scene_sounds.append({
                        "sound_id": sound_id,
                        "description": description,
                        "file": filename,
                        "start_seconds": cue.get("start_seconds", 0.0),
                        "duration_seconds": duration
                    })
                except Exception as e:
                    print(f"[FoleyDesigner] AudioFX generation failed for '{description}': {e}")
                    scene_sounds.append({
                        "sound_id": f"foley_{sid}_{description.replace(' ', '_')[:40]}",
                        "description": f"[AUDIO UNAVAILABLE] {description}",
                        "file": None,
                        "start_seconds": cue.get("start_seconds", 0.0),
                        "duration_seconds": duration
                    })
            else:
                # No provider – text‑only cue sheet
                scene_sounds.append({
                    "sound_id": f"foley_{sid}_{description.replace(' ', '_')[:40]}",
                    "description": description,
                    "file": None,
                    "start_seconds": cue.get("start_seconds", 0.0),
                    "duration_seconds": duration
                })

        manifest["scenes"][sid] = scene_sounds

    # ---- Metadata fix ----
    clean_manifest = {"scenes": manifest["scenes"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "FoleyDesignerAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["foley_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _extract_sound_cues(action_text: str, llm_provider, env: dict, loc: dict) -> List[dict]:
    """Use LLM to extract a list of diegetic sound effects from action lines."""
    system_prompt = """You are a foley artist. Given action lines from a scene, list all implied diegetic sounds.

Output a JSON array of objects with:
- "description": a clear, short description of the sound (e.g., "heavy footsteps on wooden floor")
- "start_seconds": estimated time from scene start (0 if unknown)
- "duration_seconds": estimated length (default 2.0)

Include environmental sounds (rain, wind, neon hum, distant traffic) if mentioned.
If no sounds are implied, output an empty array [].
Output ONLY valid JSON array."""

    env_description = f"Weather: {env.get('weather', 'clear')}, Wind: {env.get('wind', 'calm')}, Location: {loc.get('description', '')}"
    user_prompt = f"Environment: {env_description}\nAction lines:\n{action_text}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2
        )
        return _extract_json_array(response)
    except Exception:
        return _fallback_sound_cues(action_text, env)


def _fallback_sound_cues(action_text: str, env: dict) -> List[dict]:
    """Keyword‑based fallback if LLM fails."""
    cues = []
    keywords = {
        "footstep": "footsteps on floor",
        "door": "door opening/closing",
        "gun": "gunshot",
        "glass": "glass clinking/breaking",
        "engine": "engine revving",
        "rain": "rainfall ambience",
        "wind": "wind blowing",
        "explosion": "explosion"
    }
    for word, desc in keywords.items():
        if word in action_text.lower():
            cues.append({"description": desc, "start_seconds": 0.0, "duration_seconds": 2.0})
    if env.get("weather") == "rain":
        cues.append({"description": "continuous rain ambience", "start_seconds": 0.0, "duration_seconds": 30.0})
    return cues


def _extract_json_array(response: str) -> List[dict]:
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "sounds" in data:
            return data["sounds"]
    except json.JSONDecodeError:
        pass
    match = re.search(r'\[[\s\S]*\]', response)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return []
