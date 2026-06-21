"""
Agent 16: Cinematographer Agent
Assigns definitive camera and lighting specifications to every shot in the storyboard.
Produces a per‑shot cinematography plan that drives the Layout Agent,
Lighting Consistency Agent, and Render Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    shots = input_slices.get("storyboard", {}).get("shots", [])
    style_guide = input_slices.get("style_guide", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    tone = input_slices.get("tone_analysis", {})

    if not shots:
        empty = {"shots": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "CinematographerAgent",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"cinematography.json": final_json.encode("utf-8")}

    # 1. Build compact shot summaries
    shot_summaries = _build_shot_summaries(shots)

    # 2. Extract style defaults
    cam_defaults = style_guide.get("camera", {})
    light_defaults = style_guide.get("lighting", {})

    # 3. LLM‑based cinematography planning
    system_prompt = _build_system_prompt()
    user_prompt = (
        f"Style defaults:\nCamera: {json.dumps(cam_defaults)}\nLighting: {json.dumps(light_defaults)}\n\n"
        f"Shot list:\n{shot_summaries}"
    )

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=12288
        )
        cine_data = _extract_json(response)
    except Exception:
        cine_data = _fallback_cinematography(shots, cam_defaults, light_defaults)

    # 4. Validate and fill
    cine_data = _validate_and_fill(cine_data, shots, cam_defaults, light_defaults)

    # 5. Compute content hash WITHOUT _meta
    clean_data = {k: v for k, v in cine_data.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # 6. Add metadata
    cine_data["_meta"] = {
        "agent": "CinematographerAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(cine_data, indent=2, ensure_ascii=False)
    return {"cinematography.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a cinematographer. For each shot, provide precise camera and lighting specifications as JSON.

For each shot ID, provide an object with:
- "camera": {
    "focal_length_mm": number,
    "aperture": string (e.g., "T2.8"),
    "focus_distance_m": approximate focus distance in meters,
    "angle": "eye-level", "low", "high", "dutch", "overhead",
    "height_m": camera height from floor (typical 1.6m for eye-level),
    "movement": "static", "push-in", "dolly_left", "dolly_right", "pan", "tilt", "handheld", "crane"
  }
- "lighting_plan": {
    "key_light": {
      "intensity": 1.0 is normal,
      "color_temp_k": 3200 or 5600,
      "position": { "x": float, "y": float, "z": float } if you can estimate from the scene geography
    },
    "fill_light": {
      "intensity": 0.0-1.0,
      "color_temp_k": 3200 or 5600
    },
    "notes": any additional lighting notes (e.g., "motivated by flickering neon sign")
  }

Use the global style defaults as a baseline, but adapt each shot to the action, mood, and geography.
For static wide shots, use deeper focus (T5.6, focus_distance 10m). For close-ups, use shallow focus (T1.8, focus_distance 1.5m).
Output ONLY a valid JSON object with top-level key "shots"."""


def _build_shot_summaries(shots: List[dict]) -> str:
    parts = []
    for shot in shots:
        parts.append(
            f"{shot['id']} ({shot.get('type', '')}): {shot.get('description', '')} "
            f"[Location: {shot.get('location', '')}, Characters: {shot.get('characters_in_frame', [])}]"
        )
    return "\n".join(parts)


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


def _fallback_cinematography(shots: List[dict], cam_defaults: dict, light_defaults: dict) -> dict:
    default_focal = _focal_to_mm(cam_defaults.get("preferred_lens", "35mm"))
    default_aperture = cam_defaults.get("aperture", "T2.8")
    default_movement = cam_defaults.get("movement", "static")
    key_temp = int(light_defaults.get("key_color", "3200K").replace("K", ""))
    fill_temp = int(light_defaults.get("fill_color", "5600K").replace("K", ""))

    cine = {"shots": {}}
    for shot in shots:
        cine["shots"][shot["id"]] = {
            "camera": {
                "focal_length_mm": default_focal,
                "aperture": default_aperture,
                "focus_distance_m": 3.0,
                "angle": "eye-level",
                "height_m": 1.6,
                "movement": default_movement
            },
            "lighting_plan": {
                "key_light": {"intensity": 1.0, "color_temp_k": key_temp, "position": {"x": 2.0, "y": -3.0, "z": 2.5}},
                "fill_light": {"intensity": 0.3, "color_temp_k": fill_temp},
                "notes": ""
            }
        }
    return cine


def _focal_to_mm(focal_str: str) -> float:
    match = re.search(r'(\d+)', focal_str)
    return float(match.group(1)) if match else 35.0


def _validate_and_fill(cine_data: dict, shots: List[dict], cam_defaults: dict, light_defaults: dict) -> dict:
    cine_data.setdefault("shots", {})
    default_focal = _focal_to_mm(cam_defaults.get("preferred_lens", "35mm"))
    default_aperture = cam_defaults.get("aperture", "T2.8")
    default_movement = cam_defaults.get("movement", "static")
    key_temp = int(light_defaults.get("key_color", "3200K").replace("K", ""))
    fill_temp = int(light_defaults.get("fill_color", "5600K").replace("K", ""))

    default_shot = {
        "camera": {
            "focal_length_mm": default_focal,
            "aperture": default_aperture,
            "focus_distance_m": 3.0,
            "angle": "eye-level",
            "height_m": 1.6,
            "movement": default_movement
        },
        "lighting_plan": {
            "key_light": {"intensity": 1.0, "color_temp_k": key_temp, "position": {"x": 2.0, "y": -3.0, "z": 2.5}},
            "fill_light": {"intensity": 0.3, "color_temp_k": fill_temp},
            "notes": ""
        }
    }

    for shot in shots:
        sid = shot["id"]
        if sid not in cine_data["shots"]:
            cine_data["shots"][sid] = json.loads(json.dumps(default_shot))
        else:
            for key in default_shot["camera"]:
                if key not in cine_data["shots"][sid].get("camera", {}):
                    cine_data["shots"][sid].setdefault("camera", {})[key] = default_shot["camera"][key]
            cine_data["shots"][sid].setdefault("lighting_plan", default_shot["lighting_plan"])
    return cine_data
