"""
Agent 6: Character Persona Agent
Generates a detailed psychological profile for each character:
Big Five personality traits, archetype, speaking style, emotional range,
motivations, fears, relationships, and character arc.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    tone_analysis = input_slices.get("tone_analysis", {})

    characters = parsed_script.get("characters", [])
    scenes = parsed_script.get("scenes", [])

    if not characters:
        empty = {"characters": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "CharacterPersonaAgent",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"character_personas.json": final_json.encode("utf-8")}

    # 1. Build per‑character summaries with dialogue samples
    char_summaries = _build_character_summaries(characters, scenes)

    # 2. LLM‑based persona generation
    system_prompt = _build_system_prompt()
    user_prompt = f"Film tone: {tone_analysis.get('dominant_genre_tone', 'neutral')}\n\nCharacter summaries:\n{char_summaries}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=8192
        )
        personas = _extract_json(response)
    except Exception:
        personas = _fallback_personas(characters)

    # 3. Validate and fill missing characters
    personas = _validate_and_fill(personas, characters)

    # 4. Compute content hash WITHOUT _meta
    clean_data = {k: v for k, v in personas.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # 5. Add metadata
    personas["_meta"] = {
        "agent": "CharacterPersonaAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(personas, indent=2, ensure_ascii=False)
    return {"character_personas.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a character psychologist. For each character, produce a detailed persona profile as JSON.

For each character, include these EXACT keys:
- "personality_traits": object with Big Five scores (openness, conscientiousness, extraversion, agreeableness, neuroticism), each 0.0–1.0.
- "archetype": narrative archetype label (e.g., "wounded_hero", "mentor", "trickster", "shadow", "herald", "everyman").
- "speaking_style": how they talk – pace, vocabulary, tone, quirks.
- "emotional_range": array of emotions they display (e.g., ["grief", "determination", "dark_humor"]).
- "motivations": array of driving goals.
- "fears": array of deep fears.
- "relationships": object mapping other character names to a one‑line description of the dynamic.
- "character_arc": one sentence summarizing their emotional journey.

Base your analysis ONLY on the provided script content. Do not invent backstories.
Output ONLY valid JSON. Top key must be "characters"."""


def _build_character_summaries(characters: List[dict], scenes: List[dict]) -> str:
    parts = []
    for char in characters:
        name = char["name"]
        lines = []
        for scene in scenes:
            for d in scene.get("dialogue", []):
                if d.get("character") == name:
                    lines.append(d.get("line", ""))
        dialogue_sample = " | ".join(lines[:10])
        description = char.get("description_from_script", "No description")
        parts.append(f"{name}:\n  Description: {description}\n  Dialogue sample: {dialogue_sample}")
    return "\n\n".join(parts)


def _extract_json(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r'\{[\s\S]*\}', response)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _fallback_personas(characters: List[dict]) -> dict:
    personas = {"characters": {}}
    for char in characters:
        name = char["name"]
        personas["characters"][name] = {
            "personality_traits": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
            "archetype": "everyman",
            "speaking_style": "neutral",
            "emotional_range": ["neutral"],
            "motivations": [],
            "fears": [],
            "relationships": {},
            "character_arc": "Undefined."
        }
    return personas


def _validate_and_fill(personas: dict, characters: List[dict]) -> dict:
    personas.setdefault("characters", {})
    default_persona = {
        "personality_traits": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
        "archetype": "everyman",
        "speaking_style": "neutral",
        "emotional_range": ["neutral"],
        "motivations": [],
        "fears": [],
        "relationships": {},
        "character_arc": "Undefined."
    }
    for char in characters:
        name = char["name"]
        if name not in personas["characters"]:
            personas["characters"][name] = default_persona.copy()
        else:
            for key, val in default_persona.items():
                if key not in personas["characters"][name]:
                    personas["characters"][name][key] = val
    return personas
