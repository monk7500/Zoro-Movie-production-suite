"""
Agent 17: Dialogue Breakdown Agent
Transforms the parsed script's dialogue into a structured, machine‑readable line table
with per‑character delivery instructions (emotion, intensity, pace, volume, context).
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    tone_analysis = input_slices.get("tone_analysis", {})
    personas = input_slices.get("personas", {}).get("characters", {})

    scenes = parsed_script.get("scenes", [])
    tone_scenes = tone_analysis.get("scenes", {})

    output_scenes = {}
    char_index = {}

    for scene in scenes:
        sid = scene["id"]
        tone_info = tone_scenes.get(sid, {})
        subtext = tone_info.get("subtext", "")
        primary_emotion = tone_info.get("primary_emotion", "neutral")
        scene_intensity = tone_info.get("intensity", 0.5)
        scene_pacing = tone_info.get("pacing", "moderate")

        lines_out = []
        for i, line in enumerate(scene.get("dialogue", [])):
            char_name = line.get("character", "")
            persona = personas.get(char_name, {})
            emotional_range = persona.get("emotional_range", ["neutral"])

            delivery = {
                "emotion": primary_emotion if primary_emotion in emotional_range else (emotional_range[0] if emotional_range else "neutral"),
                "intensity": scene_intensity,
                "pace": scene_pacing,
                "volume": _estimate_volume(primary_emotion, scene_intensity),
                "context": subtext
            }

            line_id = f"{sid}_D{i+1:03d}"
            line_out = {
                "line_id": line_id,
                "character": char_name,
                "text": line.get("line", ""),
                "parenthetical": line.get("parenthetical", ""),
                "delivery_notes": delivery
            }
            lines_out.append(line_out)

            if char_name not in char_index:
                char_index[char_name] = {"total_lines": 0, "line_ids": []}
            char_index[char_name]["total_lines"] += 1
            char_index[char_name]["line_ids"].append(line_id)

        output_scenes[sid] = {
            "scene_id": sid,
            "heading": scene.get("heading", ""),
            "dialogue": lines_out
        }

    result = {"scenes": output_scenes, "characters": char_index}

    # ---- Metadata fix ----
    clean_data = {k: v for k, v in result.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    result["_meta"] = {
        "agent": "DialogueBreakdownAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(result, indent=2, ensure_ascii=False)
    return {"dialogue_breakdown.json": final_json.encode("utf-8")}


def _estimate_volume(emotion: str, intensity: float) -> str:
    loud_emotions = {"rage", "anger", "explosive rage", "panic", "triumph", "battle cry"}
    quiet_emotions = {"melancholy", "whisper", "fear", "sorrow", "grief", "quiet despair"}
    if emotion in loud_emotions:
        return "loud"
    if emotion in quiet_emotions:
        return "low"
    if intensity > 0.7:
        return "medium-loud"
    if intensity < 0.3:
        return "low"
    return "medium"
