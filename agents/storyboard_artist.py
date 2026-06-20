"""
Agent 15: Storyboard Artist
Generates a complete cinematic storyboard for the entire film.
Each shot gets a keyframe image (or text description), camera annotations,
character placement, and a manifest linking every shot to its frames.
Uses a pluggable ImageProvider or falls back to LLM text descriptions.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        image_provider=None) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    character_visuals = input_slices.get("character_visuals", {}).get("characters", {})
    locations = input_slices.get("location_profiles", {}).get("locations", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    style_guide = input_slices.get("style_guide", {})
    tone = input_slices.get("tone_analysis", {})

    scenes = parsed_script.get("scenes", [])
    if not scenes:
        empty = {"shots": [], "total_shots": 0}
        return {"storyboard_manifest.json": json.dumps(empty, indent=2).encode("utf-8")}

    # 1. Generate shot list via LLM
    shots = _generate_shot_list(scenes, tone, llm_provider)

    # 2. Generate keyframes for each shot
    output_files = {}
    style_mood = style_guide.get("color_palette", {}).get("mood", "cinematic")
    style_lighting = style_guide.get("lighting", {}).get("mood", "neutral lighting")

    manifest = {"shots": [], "total_shots": len(shots)}

    for shot in shots:
        shot_id = shot["id"]
        chars_in_frame = shot.get("characters_in_frame", [])
        location = shot.get("location", "")

        # Build character description
        char_desc_parts = []
        for name in chars_in_frame:
            char_vis = character_visuals.get(name, {})
            if char_vis:
                char_desc_parts.append(f"{name} (consistent with reference)")
            else:
                char_desc_parts.append(name)
        char_desc = ", ".join(char_desc_parts) if char_desc_parts else ""

        loc_desc = ""
        if location and location in locations:
            loc_desc = locations[location].get("description", location)

        prompt = (
            f"Storyboard keyframe, {shot.get('type', 'wide')} shot, "
            f"{shot.get('description', '')}, "
            f"Characters: {char_desc}, "
            f"Location: {loc_desc}, "
            f"Style: {style_mood}, Lighting: {style_lighting}, "
            f"Camera: {shot.get('camera', {}).get('focal_length', '35mm')} lens, "
            f"{shot.get('camera', {}).get('angle', 'eye-level')}, "
            f"consistent character references, concept art, high detail"
        )

        if image_provider:
            try:
                img_bytes = image_provider.generate(
                    prompt=prompt,
                    negative="deformed, extra limbs, blurry, inconsistent characters, wrong face",
                    width=1920, height=1080,
                    seed=_stable_seed(shot_id)
                )
                filename = f"storyboard/{shot_id}.png"
                output_files[filename] = img_bytes
                shot["keyframe"] = filename
            except Exception:
                shot["keyframe_description"] = _generate_shot_description(prompt, llm_provider)
        else:
            shot["keyframe_description"] = _generate_shot_description(prompt, llm_provider)

        manifest["shots"].append(shot)

    output_files["storyboard_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _generate_shot_list(scenes: List[dict], tone: dict, llm_provider) -> List[dict]:
    """Use LLM to break down each scene into a shot list."""
    scene_summaries = []
    for scene in scenes:
        actions = " | ".join(scene.get("action_lines", [])[:5])
        chars = ", ".join(scene.get("characters_in_scene", []))
        scene_summaries.append(
            f"{scene['id']} ({scene['heading']}): {actions} [Characters: {chars}]"
        )
    script_summary = "\n".join(scene_summaries)

    system_prompt = """You are a storyboard artist and cinematographer. Break down the provided script into a shot list.

For each scene, produce 1-5 shots. Each shot must have:
- "id": unique shot ID (e.g., SHOT_01)
- "scene": scene ID it belongs to
- "type": "wide", "medium", "close-up", "over-the-shoulder", "insert", "cutaway", "POV"
- "description": concise visual description including character positions
- "camera": { "focal_length": string, "aperture": string, "angle": string, "movement": string }
- "characters_in_frame": list of visible characters
- "location": scene location

Output ONLY a valid JSON object with key "shots"."""

    try:
        response = llm_provider.generate(
            prompt=f"Script summary:\n{script_summary}",
            system=system_prompt,
            temperature=0.3,
            max_tokens=12288
        )
        shot_data = _extract_json(response)
        shots = shot_data.get("shots", [])
    except Exception:
        shots = _fallback_shot_list(scenes)

    if not shots:
        shots = _fallback_shot_list(scenes)
    return shots


def _fallback_shot_list(scenes: List[dict]) -> List[dict]:
    shots = []
    idx = 1
    for scene in scenes:
        shots.append({
            "id": f"SHOT_{idx:02d}",
            "scene": scene["id"],
            "type": "wide",
            "description": f"Wide shot of {scene.get('heading', '')}. {scene.get('action_lines', [''])[0]}",
            "camera": {"focal_length": "35mm", "aperture": "T2.8", "angle": "eye-level", "movement": "static"},
            "characters_in_frame": scene.get("characters_in_scene", []),
            "location": scene.get("location", "")
        })
        idx += 1
    return shots


def _generate_shot_description(prompt: str, llm_provider) -> str:
    system = """You are a storyboard artist. Describe the following keyframe in extreme visual detail.
Include camera angle, lighting, character positions, expressions, props, and background.
Write as if describing a finished painting or film still."""
    try:
        return llm_provider.generate(prompt=prompt, system=system, temperature=0.7)
    except:
        return f"Keyframe: {prompt}"


def _stable_seed(shot_id: str) -> int:
    return int(hashlib.sha256(shot_id.encode()).hexdigest()[:8], 16) % 100000


def _extract_json(response: str) -> dict:
    try: return json.loads(response)
    except: pass
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if fence:
        try: return json.loads(fence.group(1))
        except: pass
    brace = re.search(r'\{[\s\S]*\}', response)
    if brace:
        try: return json.loads(brace.group(0))
        except: pass
    return {}
