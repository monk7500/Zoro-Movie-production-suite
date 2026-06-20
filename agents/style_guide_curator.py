"""
Agent 14: Style Guide Curator
Produces the definitive Visual Style Guide from the tone analysis,
any uploaded reference images, and the creator's director notes.
Governs the Storyboard Artist, Cinematographer, Lighting Consistency Agent,
Color Grading Agent, and Render Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    tone = input_slices.get("tone_analysis", {})
    refs = input_slices.get("references", [])
    director_notes = input_slices.get("director_notes", "")

    genre_tone = tone.get("dominant_genre_tone", "neutral cinematic")

    # Build reference summary
    ref_summary = ""
    if refs:
        ref_names = [r.get("filename", "unknown") for r in refs]
        ref_summary = f"Reference images: {', '.join(ref_names)}"

    # 1. LLM‑based style guide generation
    system_prompt = _build_system_prompt()
    user_prompt = f"Genre tone: {genre_tone}\n{ref_summary}\nDirector notes: {director_notes}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.4,
            max_tokens=8192
        )
        style = _extract_json(response)
    except Exception:
        style = _fallback_style_guide(genre_tone)

    # 2. Validate and fill missing sections
    style = _validate_and_fill(style, genre_tone)

    # 3. Add metadata
    output_json = json.dumps(style, indent=2, ensure_ascii=False)
    style["_meta"] = {
        "agent": "StyleGuideCurator",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"style_guide.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a director of photography and production designer. Create a detailed visual style guide for the film as a JSON object.

Include the following sections (use EXACTLY these keys):
- "color_palette": {
    "dominant": array of hex color strings (e.g., ["#0A1C2E", "#F4A261"]),
    "accent": array of accent hex colors,
    "mood": one‑sentence description of the color mood
  }
- "lighting": {
    "key_ratio": typical key‑to‑fill ratio (e.g., "4:1"),
    "fill_color": color temperature of fill light (e.g., "cool 5600K"),
    "key_color": color temperature of key light (e.g., "warm 3200K"),
    "practical_sources": array of practical light types (e.g., ["neon", "streetlamps"]),
    "mood": lighting mood description (e.g., "low-key noir with neon accents")
  }
- "camera": {
    "preferred_lens": lens type and focal length range (e.g., "35mm anamorphic"),
    "aperture": typical T‑stop (e.g., "T2.8"),
    "depth_of_field": how depth of field is used (e.g., "shallow for close-ups, deep for wide shots"),
    "movement": camera movement style (e.g., "handheld when tense, smooth dolly otherwise"),
    "film_stock": film stock or digital emulation (e.g., "Kodak Vision3 500T emulation")
  }
- "post_processing": {
    "grain": description (e.g., "subtle 35mm grain"),
    "vignette": description (e.g., "slight"),
    "halation": description (e.g., "bloom on highlights"),
    "saturation": number (1.0 = neutral),
    "contrast": number (1.0 = neutral)
  }
- "rules": an array of visual rules (e.g., "Never use pure white light.")

Base your decisions on the genre tone and any reference images or director notes. If minimal direction, default to cinematic neutral with 3:1 key ratio and warm/cool split.
Output ONLY valid JSON. No markdown."""


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


def _fallback_style_guide(genre_tone: str) -> dict:
    return {
        "color_palette": {
            "dominant": ["#0A1C2E", "#F4A261"],
            "accent": ["#E76F51"],
            "mood": f"Default cinematic palette for {genre_tone}"
        },
        "lighting": {
            "key_ratio": "3:1",
            "fill_color": "cool 5600K",
            "key_color": "warm 3200K",
            "practical_sources": [],
            "mood": "neutral"
        },
        "camera": {
            "preferred_lens": "35mm",
            "aperture": "T2.8",
            "depth_of_field": "moderate",
            "movement": "smooth dolly",
            "film_stock": "digital"
        },
        "post_processing": {
            "grain": "none",
            "vignette": "none",
            "halation": "none",
            "saturation": 1.0,
            "contrast": 1.0
        },
        "rules": []
    }


def _validate_and_fill(style: dict, genre_tone: str) -> dict:
    default = _fallback_style_guide(genre_tone)
    for section in default:
        if section not in style:
            style[section] = default[section]
        elif isinstance(default[section], dict):
            for key, val in default[section].items():
                if key not in style[section]:
                    style[section][key] = val
    return style
