"""
Agent 25: Animation Agent
Generates per‑shot animation data: body motion, facial expressions, and mouth shapes.
In cinematic mode, produces mouth‑shape sequences from dialogue audio.
In narration mode, produces only subtle emotional expressions.
Uses pluggable MotionProvider and FacialAnimationProvider, or falls back to text.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        motion_provider=None, facial_provider=None) -> Dict[str, bytes]:
    layout = input_slices.get("layout", {}).get("shots", {})
    dialogue = input_slices.get("dialogue_breakdown", {}).get("scenes", {})
    voice_manifest = input_slices.get("voice_audio", {}).get("characters", {})
    personas = input_slices.get("character_personas", {}).get("characters", {})
    wardrobe = input_slices.get("wardrobe_timeline", {}).get("characters", {})
    cinematography = input_slices.get("cinematography", {}).get("shots", {})
    action_choreo = input_slices.get("action_choreography", {}).get("scenes", {})
    mode = input_slices.get("mode", "cinematic")

    output_files = {}
    manifest = {"shots": {}}

    for shot_id, shot_layout in layout.items():
        duration = _estimate_shot_duration(shot_id, dialogue, voice_manifest, mode)
        frame_rate = 24
        total_frames = int(duration * frame_rate)

        shot_anim = {"frame_rate": frame_rate, "duration_seconds": duration, "characters": {}}
        mouth_data = {} if mode == "cinematic" else None

        for entity in shot_layout.get("entities", []):
            if entity["type"] != "character":
                continue

            char_name = entity["id"]
            start_pos = entity["position"]
            scene_id = _shot_id_to_scene_id(shot_id)

            persona = personas.get(char_name, {})
            primary_emotion = persona.get("emotional_range", ["neutral"])[0]
            physical = _get_physical_state(char_name, scene_id, wardrobe)

            actions = _get_actions_for_char(char_name, scene_id, action_choreo)

            # ---- Body Motion ----
            if motion_provider:
                motion = motion_provider.generate_body_motion(
                    character_id=char_name,
                    start_position=start_pos,
                    duration_sec=duration,
                    frame_rate=frame_rate,
                    emotion=primary_emotion,
                    physical_state=physical,
                    action_sequence=actions,
                    shot_context=shot_id
                )
            else:
                motion = _generate_motion_description(
                    char_name, start_pos, duration, frame_rate,
                    primary_emotion, physical, actions, llm_provider
                )

            # ---- Facial Expressions ----
            if facial_provider:
                emotion_curve = _build_emotion_curve(duration, frame_rate, primary_emotion)
                expressions = facial_provider.generate_expressions(
                    character_id=char_name,
                    duration_sec=duration,
                    frame_rate=frame_rate,
                    emotion_curve=emotion_curve
                )
            else:
                expressions = {
                    "type": "text_description",
                    "description": f"Facial expressions reflecting {primary_emotion}"
                }

            # ---- Mouth Shapes (cinematic only) ----
            if mode == "cinematic" and facial_provider:
                audio_path = _get_audio_for_shot_char(shot_id, char_name, voice_manifest, dialogue)
                if audio_path:
                    mouth = facial_provider.generate_mouth_shapes(
                        character_id=char_name,
                        audio_file_path=audio_path,
                        frame_rate=frame_rate
                    )
                    mouth_data[char_name] = mouth
            elif mode == "cinematic" and not facial_provider:
                mouth_data[char_name] = {
                    "type": "text_description",
                    "description": f"Mouth shapes synchronized with dialogue for {char_name}"
                }

            shot_anim["characters"][char_name] = {
                "skeleton": "human_female",
                "motion": motion,
                "expressions": expressions
            }

        # Write per‑shot files
        shot_dir = f"animation/{shot_id}"
        output_files[f"{shot_dir}/animation_data.json"] = json.dumps(shot_anim, indent=2).encode("utf-8")

        if mouth_data is not None:
            output_files[f"{shot_dir}/mouth_shapes.json"] = json.dumps(mouth_data, indent=2).encode("utf-8")

        manifest["shots"][shot_id] = {
            "animation_file": f"{shot_dir}/animation_data.json",
            "mouth_shapes_file": f"{shot_dir}/mouth_shapes.json" if mouth_data is not None else None,
            "duration_seconds": duration,
            "characters_animated": [e["id"] for e in shot_layout.get("entities", []) if e["type"] == "character"]
        }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "AnimationAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["animation_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _estimate_shot_duration(shot_id, dialogue, voice_manifest, mode):
    if mode == "cinematic":
        return 8.0
    return 5.0


def _shot_id_to_scene_id(shot_id):
    return "S01"


def _get_physical_state(char_name, scene_id, wardrobe):
    timeline = wardrobe.get(char_name, {}).get("timeline", [])
    for entry in timeline:
        if entry.get("scene") == scene_id:
            return entry.get("physical", {})
    return {}


def _get_actions_for_char(char_name, scene_id, action_choreo):
    scene_choreo = action_choreo.get(scene_id, {}).get("characters", {})
    char_choreo = scene_choreo.get(char_name, {})
    return char_choreo.get("actions", [])


def _get_audio_for_shot_char(shot_id, char_name, voice_manifest, dialogue):
    char_voice = voice_manifest.get(char_name, {})
    lines = char_voice.get("lines", {})
    for line_id, audio_path in lines.items():
        if _line_in_shot(line_id, shot_id):
            return audio_path
    return None


def _line_in_shot(line_id, shot_id):
    return True


def _build_emotion_curve(duration, frame_rate, primary_emotion):
    return [{"time_sec": 0.0, "emotion": primary_emotion}, {"time_sec": duration, "emotion": primary_emotion}]


def _generate_motion_description(char_name, start_pos, duration, frame_rate, emotion, physical, actions, llm_provider):
    if actions:
        desc = "; ".join([a.get("style", a.get("type", "")) for a in actions])
        return {"type": "text_description", "description": f"{char_name}: {desc}"}
    return {"type": "text_description", "description": f"{char_name}: idle {emotion}"}
