"""
Agent 1: Script Parser
Converts raw screenplay text (Fountain, plain text) into structured JSON.
Extracts scenes, characters, dialogue, action lines, and ALL entities.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    raw_script = input_slices.get("script_raw", "")
    mode = input_slices.get("mode", "cinematic")

    # ---- 1. Pre‑parse with regex (fast, always works) ----
    pre_parsed = _pre_parse(raw_script)

    # ---- 2. LLM‑based full parse ----
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

    # ---- 3. Validate and fill missing fields ----
    parsed = _validate_and_fill(parsed, pre_parsed)

    # ---- 4. Extract all entities if missing ----
    if not parsed.get("entities"):
        parsed["entities"] = _extract_entities(parsed)

    # ---- 5. Enrich character descriptions from action lines ----
    parsed["characters"] = _enrich_character_descriptions(parsed)

    # ---- 6. Compute content hash WITHOUT _meta ----
    clean_data = {k: v for k, v in parsed.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # ---- 7. Add metadata ----
    parsed["_meta"] = {
        "agent": "ScriptParser",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---- 8. Serialize final output WITH metadata ----
    final_json = json.dumps(parsed, indent=2, ensure_ascii=False)
    return {"parsed_script.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a professional screenplay parser. Convert the given screenplay into a strict JSON structure.

RULES:
1. Identify all scenes from their headings (INT./EXT., location, time of day). Scene IDs must be sequential: S01, S02, etc.
2. For each scene, extract:
   - ALL action lines (exactly as written)
   - ALL dialogue blocks with: character name, parenthetical (if any), and line text
   - characters_in_scene: list of character names who appear or are mentioned in action lines
   - mentioned_props: any significant physical objects described in the scene
3. Build a global character list ("characters") with:
   - name: the character's name as it appears in dialogue headings
   - aliases: other names used for the same character (e.g., "DR. JANE" = "JANE")
   - first_appearance: the scene ID where they first appear
   - description_from_script: any physical description found in action lines near their introduction (exact text). Do NOT invent descriptions.
4. Build a global entity list ("entities") with ALL tangible nouns that are significant to the story or may appear on screen:
   - name: a descriptive identifier (e.g., "coffee_mug", "getaway_car", "crow", "neon_sign")
   - type: one of "vehicle", "animal", "machine", "prop", "furniture", "weapon", "clothing", "accessory", "food", "plant", "building_part"
   - subtype: more specific (e.g., "car", "bird", "lamp") if clear
   - first_mentioned: scene ID
   - context: the action line or dialogue where it appears
   - attributes: any described properties (color, material, condition, state) as key-value pairs
5. Build a simple prop list ("props") for backward compatibility: name, first_mentioned, context.
6. Output ONLY valid JSON. No markdown. No commentary.
7. The JSON top-level keys must be: "title", "scenes", "characters", "entities", "props".
8. If the script is in Fountain format, lines starting with '>' are center-aligned, '.' is forced scene heading — treat them appropriately.
9. If a character's name is in ALL CAPS in action lines, they are being introduced — capture their description.
10. Do not skip any scene, any line of dialogue, or any significant entity."""


# ---------------------------------------------------------------------------
# Pre‑parser (fallback when LLM is unavailable)
# ---------------------------------------------------------------------------
def _pre_parse(raw_script: str) -> dict:
    scenes = []
    characters = {}
    entities = []
    props = {}

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


# ---------------------------------------------------------------------------
# JSON extraction (handles LLM quirks)
# ---------------------------------------------------------------------------
def _extract_json(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    # Try markdown code fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding the first { ... } block
    brace_match = re.search(r'\{[\s\S]*\}', response)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    # If all fails, return empty skeleton
    return {"title": "Untitled", "scenes": [], "characters": [], "entities": [], "props": []}


# ---------------------------------------------------------------------------
# Validation and gap‑filling
# ---------------------------------------------------------------------------
def _validate_and_fill(parsed: dict, fallback: dict) -> dict:
    if "title" not in parsed:
        parsed["title"] = fallback.get("title", "Untitled")
    if "scenes" not in parsed or not parsed["scenes"]:
        parsed["scenes"] = fallback.get("scenes", [])
    if "characters" not in parsed:
        parsed["characters"] = fallback.get("characters", [])
    if "entities" not in parsed:
        parsed["entities"] = fallback.get("entities", [])
    if "props" not in parsed:
        parsed["props"] = fallback.get("props", [])

    # Ensure every scene has required sub‑fields
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

    # Build character list from dialogue if missing
    if not parsed["characters"]:
        all_chars = {}
        for scene in parsed["scenes"]:
            for d in scene.get("dialogue", []):
                name = d.get("character", "")
                if name and name not in all_chars:
                    all_chars[name] = {
                        "name": name,
                        "aliases": [],
                        "first_appearance": scene["id"],
                        "description_from_script": None
                    }
        parsed["characters"] = list(all_chars.values())

    return parsed


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------
def _extract_entities(parsed: dict) -> list:
    entities = []
    seen = set()

    # Entity patterns: common nouns that are likely props, vehicles, animals, etc.
    patterns = {
        r'\b(car|truck|van|motorcycle|bus|train|ship|plane|helicopter|tank|jeep|suv|sedan|coupe|convertible)\b': "vehicle",
        r'\b(dog|cat|bird|crow|raven|horse|rat|snake|fish|wolf|eagle|hawk|pigeon|sparrow)\b': "animal",
        r'\b(gun|pistol|rifle|knife|sword|revolver|shotgun|crossbow|grenade|bomb|explosive)\b': "weapon",
        r'\b(phone|computer|laptop|tablet|screen|monitor|keyboard|drone|robot|implant|holo(?:gram|graphic|display)?)\b': "machine",
        r'\b(chair|table|desk|bed|couch|sofa|stool|counter|bar|shelf|dresser|cabinet)\b': "furniture",
        r'\b(bottle|glass|mug|cup|plate|bowl|bag|backpack|briefcase|suitcase|box|crate)\b': "prop",
        r'\b(jacket|coat|hat|boot|shoe|glove|scarf|mask|helmet|uniform|dress|suit)\b': "clothing",
    }

    for scene in parsed.get("scenes", []):
        # Check action lines
        for line in scene.get("action_lines", []):
            for pattern, entity_type in patterns.items():
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    name = match.group(1).lower()
                    context = line
                    if name not in seen:
                        seen.add(name)
                        entities.append({
                            "name": name,
                            "type": entity_type,
                            "subtype": name,
                            "first_mentioned": scene["id"],
                            "context": context,
                            "attributes": {}
                        })
        # Also check dialogue for mentioned objects
        for d in scene.get("dialogue", []):
            line = d.get("line", "")
            for pattern, entity_type in patterns.items():
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    name = match.group(1).lower()
                    if name not in seen:
                        seen.add(name)
                        entities.append({
                            "name": name,
                            "type": entity_type,
                            "subtype": name,
                            "first_mentioned": scene["id"],
                            "context": line,
                            "attributes": {}
                        })
    return entities


# ---------------------------------------------------------------------------
# Character description enrichment
# ---------------------------------------------------------------------------
def _enrich_character_descriptions(parsed: dict) -> list:
    characters = parsed.get("characters", [])
    scenes = parsed.get("scenes", [])

    for char in characters:
        if char.get("description_from_script"):
            continue
        name = char["name"]
        first_scene_id = char.get("first_appearance", "")

        for scene in scenes:
            if scene["id"] == first_scene_id:
                for line in scene.get("action_lines", []):
                    if re.search(rf'\b{re.escape(name)}\b', line, re.IGNORECASE):
                        char["description_from_script"] = line
                        break
                break

    return characters
