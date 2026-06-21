"""
Agent 7: Voice Profile Agent
Defines vocal characteristics for every character: pitch, timbre, accent,
pace, emotional range, and descriptive summary. Drives the Voice Performance Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    characters = input_slices.get("characters", [])
    personas = input_slices.get("personas", {}).get("characters", {})
    tone = input_slices.get("tone_analysis", {})

    if not characters:
        empty = {"characters": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "VoiceProfileAgent",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"voice_profiles.json": final_json.encode("utf-8")}

    # 1. Build character summaries with persona context
    char_summaries = _build_character_summaries(characters, personas)

    # 2. LLM‑based voice casting
    system_prompt = _build_system_prompt()
    film_tone = tone.get("dominant_genre_tone", "neutral")
    user_prompt = f"Film tone: {film_tone}\n\nCharacter summaries:\n{char_summaries}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=8192
        )
        profiles = _extract_json(response)
    except Exception:
        profiles = _fallback_profiles(characters)

    # 3. Validate and fill
    profiles = _validate_and_fill(profiles, characters)

    # 4. Compute content hash WITHOUT _meta
    clean_data = {k: v for k, v in profiles.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # 5. Add metadata
    profiles["_meta"] = {
        "agent": "VoiceProfileAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(profiles, indent=2, ensure_ascii=False)
    return {"voice_profiles.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a voice casting director. For each character, provide a detailed voice profile as JSON.

For each character, include these EXACT keys:
- "pitch": "soprano", "mezzo", "contralto", "tenor", "baritone", "bass", "child", "elderly_high", "elderly_low"
- "timbre": e.g., "gravelly", "smooth", "nasal", "breathy", "rich", "thin", "raspy", "velvet", "metallic"
- "accent": e.g., "neutral American", "British RP", "Southern US", "Irish", "Australian", "French", "undefined"
- "pace": "slow", "moderate", "fast", "deliberate", "erratic"
- "emotional_range": array of emotions the voice should convey
- "age_voice": "young", "mature", "middle-aged", "elderly"
- "description": one‑sentence summary of how the character sounds

Base on script description, persona, and film tone. If no information, use neutral defaults.
Output ONLY valid JSON. Top key: "characters"."""


def _build_character_summaries(characters: List[dict], personas: dict) -> str:
    parts = []
    for char in characters:
        name = char["name"]
        desc = char.get("description_from_script", "No description")
        persona = personas.get(name, {})
        speaking = persona.get("speaking_style", "unknown")
        emotional = persona.get("emotional_range", [])
        parts.append(f"{name}: description='{desc}', speaking style='{speaking}', emotional range={emotional}")
    return "\n".join(parts)


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


def _fallback_profiles(characters: List[dict]) -> dict:
    profiles = {"characters": {}}
    for char in characters:
        name = char["name"]
        profiles["characters"][name] = {
            "pitch": "medium", "timbre": "neutral", "accent": "undefined",
            "pace": "moderate", "emotional_range": ["neutral"],
            "age_voice": "mature", "description": "Auto‑generated."
        }
    return profiles


def _validate_and_fill(profiles: dict, characters: List[dict]) -> dict:
    profiles.setdefault("characters", {})
    default_profile = {
        "pitch": "medium", "timbre": "neutral", "accent": "undefined",
        "pace": "moderate", "emotional_range": ["neutral"],
        "age_voice": "mature", "description": "Auto‑generated."
    }
    for char in characters:
        name = char["name"]
        if name not in profiles["characters"]:
            profiles["characters"][name] = default_profile.copy()
        else:
            for key, val in default_profile.items():
                if key not in profiles["characters"][name]:
                    profiles["characters"][name][key] = val
    return profiles
