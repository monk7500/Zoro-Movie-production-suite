"""
Agent 1: Script Parser
Converts raw screenplay text into structured JSON.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    raw_script = input_slices.get("script_raw", "")
    mode = input_slices.get("mode", "cinematic")

    # 1. Pre‑parse with regex (fast, always works)
    pre_parsed = _pre_parse(raw_script)

    # 2. LLM‑based full parse
    system_prompt = _build_system_prompt()
    user_prompt = f"Screenplay:\n\n{raw_script}\n\nParse this screenplay into JSON as specified."

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.1,
            max_tokens=16384
        )
        parsed = _extract_json(response)
    except Exception:
        parsed = pre_parsed   # fallback to regex parser

    # 3. Validate and fill missing fields
    parsed = _validate_and_fill(parsed, pre_parsed)

    # 4. Extract all entities if missing
    if not parsed.get("entities"):
        parsed["entities"] = _extract_entities(parsed)

    # 5. Enrich character descriptions from action lines
    parsed["characters"] = _enrich_character_descriptions(parsed)

    # 6. Add metadata
    output_json = json.dumps(parsed, indent=2, ensure_ascii=False)
    parsed["_meta"] = {
        "agent": "ScriptParser",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"parsed_script.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a professional screenplay parser. Convert the given screenplay into a strict JSON structure.

RULES:
1. Identify all scenes (INT./EXT. headings). Scene IDs: S01, S02...
2. For each scene extract:
   - ALL action lines
   - ALL dialogue blocks (character, parenthetical, line)
   - characters_in_scene (from dialogue + action lines)
   - mentioned_props (significant objects)
3. Global character list: name, aliases, first_appearance, description_from_script (exact text, no invention).
4. Global entity list: ALL tangible nouns (vehicles, animals, props, furniture, weapons, etc.).
   Each entity: name, type, subtype, first_mentioned, context, attributes.
5. Output ONLY valid JSON. Top keys: "title", "scenes", "characters", "entities", "props"."""


def _pre_parse(raw_script: str) -> dict:
    scenes, characters, props, entities = [], {}, {}, []
    lines = raw_script.split("\n")
    current_scene = None
    scene_idx = 0
    in_dialogue = False
    current_character = ""
    current_parenthetical = ""
    current_dialogue_lines = []
    scene_heading_re = re.compile(r'^(INT\.|EXT\.|INT/EXT\.|I/E\.)', re.IGNORECASE)
    character_re = re.compile(r'^[A-Z][A-Z\s\'\-]{1,30}$')

    def _flush_dialogue():
        nonlocal in_dialogue, current_character, current_parenthetical, current_dialogue_lines
        if current_character and current_dialogue_lines and current_scene:
            current_scene.setdefault("dialogue", []).append({
                "character": current_character,
                "line": " ".join(current_dialogue_lines),
                "parenthetical": current_parenthetical,
                "emotion_hint": None
            })
            if current_character not in current_scene.setdefault("characters_in_scene", []):
                current_scene["characters_in_scene"].append(current_character)
            if current_character not in characters:
                characters[current_character] = {
                    "name": current_character,
                    "aliases": [],
                    "first_appearance": current_scene["id"],
                    "description_from_script": None
                }
        current_character = ""
        current_parenthetical = ""
        current_dialogue_lines = []
        in_dialogue = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            _flush_dialogue()
            continue
        if scene_heading_re.match(stripped):
            _flush_dialogue()
            scene_idx += 1
            current_scene = {
                "id": f"S{scene_idx:02d}",
                "heading": stripped,
                "location": _extract_location(stripped),
                "time_of_day": _extract_time_of_day(stripped),
                "interior": stripped.upper().startswith("INT"),
                "action_lines": [],
                "dialogue": [],
                "characters_in_scene": [],
                "mentioned_props": []
            }
            scenes.append(current_scene)
            continue
        if not current_scene:
            continue
        if stripped.startswith("(") and stripped.endswith(")") and in_dialogue:
            current_parenthetical = stripped.strip("()")
            continue
        if character_re.match(stripped) and not in_dialogue:
            _flush_dialogue()
            current_character = stripped
            in_dialogue = True
            continue
        if in_dialogue:
            current_dialogue_lines.append(stripped)
            continue
        current_scene["action_lines"].append(stripped)

    _flush_dialogue()
    return {
        "title": "Untitled",
        "scenes": scenes,
        "characters": list(characters.values()),
        "entities": entities,
        "props": list(props.values())
    }


def _extract_location(heading: str) -> str:
    return re.sub(r'^(INT\.|EXT\.|INT/EXT\.|I/E\.)\s*', '', heading, flags=re.IGNORECASE).split(" - ")[0].strip()


def _extract_time_of_day(heading: str) -> str:
    m = re.search(r'-\s*(DAY|NIGHT|DAWN|DUSK|MORNING|AFTERNOON|EVENING|CONTINUOUS|LATER|SAME)', heading, re.IGNORECASE)
    return m.group(1).upper() if m else "DAY"


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


def _validate_and_fill(parsed: dict, fallback: dict) -> dict:
    parsed.setdefault("title", fallback.get("title", "Untitled"))
    parsed.setdefault("scenes", fallback.get("scenes", []))
    parsed.setdefault("characters", fallback.get("characters", []))
    parsed.setdefault("entities", fallback.get("entities", []))
    parsed.setdefault("props", fallback.get("props", []))
    for scene in parsed["scenes"]:
        scene.setdefault("id", f"S{parsed['scenes'].index(scene)+1:02d}")
        scene.setdefault("heading", "")
        scene.setdefault("location", _extract_location(scene.get("heading", "")))
        scene.setdefault("time_of_day", _extract_time_of_day(scene.get("heading", "")))
        scene.setdefault("interior", scene.get("heading", "").upper().startswith("INT"))
        scene.setdefault("action_lines", [])
        scene.setdefault("dialogue", [])
        scene.setdefault("characters_in_scene", [])
        scene.setdefault("mentioned_props", [])
    return parsed


def _extract_entities(parsed: dict) -> list:
    entities, seen = [], set()
    patterns = {
        r'\b(car|truck|van|motorcycle|bus|train|ship|plane|helicopter|tank)\b': "vehicle",
        r'\b(dog|cat|bird|crow|raven|horse|rat|snake|fish|wolf)\b': "animal",
        r'\b(gun|pistol|rifle|knife|sword|revolver|shotgun|crossbow|grenade)\b': "weapon",
        r'\b(phone|computer|laptop|tablet|drone|robot|holo(?:gram|display)?)\b': "machine",
        r'\b(chair|table|desk|bed|couch|stool|counter|bar)\b': "furniture",
        r'\b(bottle|glass|mug|cup|plate|bag|backpack|briefcase)\b': "prop",
        r'\b(jacket|coat|hat|boot|glove|mask|helmet|dress|suit)\b': "clothing",
    }
    for scene in parsed.get("scenes", []):
        for line in scene.get("action_lines", []) + [d.get("line", "") for d in scene.get("dialogue", [])]:
            for pat, etype in patterns.items():
                for match in re.finditer(pat, line, re.IGNORECASE):
                    name = match.group(1).lower()
                    if name not in seen:
                        seen.add(name)
                        entities.append({
                            "name": name, "type": etype, "subtype": name,
                            "first_mentioned": scene["id"], "context": line,
                            "attributes": {}
                        })
    return entities


def _enrich_character_descriptions(parsed: dict) -> list:
    characters = parsed.get("characters", [])
    scenes = parsed.get("scenes", [])
    for char in characters:
        if char.get("description_from_script"):
            continue
        name = char["name"]
        for scene in scenes:
            if scene["id"] == char.get("first_appearance", ""):
                for line in scene.get("action_lines", []):
                    if re.search(rf'\b{re.escape(name)}\b', line, re.IGNORECASE):
                        char["description_from_script"] = line
                        break
                break
    return characters
