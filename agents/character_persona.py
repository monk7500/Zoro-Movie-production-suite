"""
Agent 6: Character Persona Agent
Generates a detailed psychological profile for each character.
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

    char_summaries = _build_character_summaries(characters, scenes)

    system_prompt = _build_system_prompt()
    user_prompt = f"Film tone: {tone_analysis.get('dominant_genre_tone', 'neutral')}\n\nCharacter summaries:\n{char_summaries}"

    try:
        response = llm_provider.generate(prompt=user_prompt, system=system_prompt, temperature=0.3, max_tokens=8192)
        personas = _extract_json(response)
    except Exception:
        personas = _fallback_personas(characters)

    personas = _validate_and_fill(personas, characters)

    # ---- Metadata fix ----
    clean_data = {k: v for k, v in personas.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    personas["_meta"] = {
        "agent": "CharacterPersonaAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(personas, indent=2, ensure_ascii=False)
    return {"character_personas.json": final_json.encode("utf-8")}


# (include helper functions: _build_system_prompt, _build_character_summaries,
#  _extract_json, _fallback_personas, _validate_and_fill from earlier implementation)
