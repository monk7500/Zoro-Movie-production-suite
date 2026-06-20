"""
Agent 17: Dialogue Breakdown Agent – placeholder.
"""

import json

def run(input_slices, bible_version, llm_provider):
    parsed_script = input_slices.get("parsed_script", {})
    tone = input_slices.get("tone_analysis", {})
    personas = input_slices.get("character_personas", {}).get("characters", {})

    scenes = parsed_script.get("scenes", [])
    output_scenes = {}
    char_index = {}

    for scene in scenes:
        sid = scene["id"]
        lines_out = []
        for i, line in enumerate(scene.get("dialogue", [])):
            char_name = line.get("character", "")
            line_id = f"{sid}_D{i+1:03d}"
            lines_out.append({
                "line_id": line_id,
                "character": char_name,
                "text": line.get("line", ""),
                "parenthetical": line.get("parenthetical", ""),
                "delivery_notes": {"emotion": "neutral", "intensity": 0.5, "pace": "moderate", "volume": "medium", "context": ""}
            })
            char_index.setdefault(char_name, {"total_lines": 0, "line_ids": []})
            char_index[char_name]["total_lines"] += 1
            char_index[char_name]["line_ids"].append(line_id)
        output_scenes[sid] = {"scene_id": sid, "heading": scene.get("heading", ""), "dialogue": lines_out}

    result = {"scenes": output_scenes, "characters": char_index}
    return {"dialogue_breakdown.json": json.dumps(result).encode()}
