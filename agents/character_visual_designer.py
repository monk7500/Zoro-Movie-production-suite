"""
Agent 5: Character Visual Designer
Generates consistent character concept art: turnarounds, face sheets,
outfit variants, and age/injury/condition variants.
Uses a pluggable ImageProvider or falls back to rich text descriptions.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        image_provider=None) -> Dict[str, bytes]:
    characters = input_slices.get("characters", [])
    wardrobe = input_slices.get("wardrobe_timeline", {}).get("characters", {})
    style_guide = input_slices.get("style_guide", {})
    tone = input_slices.get("tone_analysis", {})

    output_files = {}
    manifest = {"characters": {}}

    palette_mood = style_guide.get("color_palette", {}).get("mood", "cinematic")
    lighting_mood = style_guide.get("lighting", {}).get("mood", "neutral lighting")

    for char in characters:
        name = char["name"]
        description = char.get("description_from_script") or ""

        char_wardrobe = wardrobe.get(name, {}).get("timeline", [])
        unique_states = _collect_unique_states(char_wardrobe, description)

        if image_provider:
            char_manifest = _generate_images(
                image_provider, name, description, unique_states,
                palette_mood, lighting_mood, output_files
            )
        else:
            char_manifest = _generate_text_descriptions(
                llm_provider, name, description, unique_states,
                palette_mood, lighting_mood, output_files
            )

        manifest["characters"][name] = char_manifest

    # ---- Metadata (corrected) ----
    clean_manifest = {"characters": manifest["characters"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "CharacterVisualDesigner",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# --- helper functions unchanged (omitted for brevity) ---
# Include the full _collect_unique_states, _generate_images, _generate_text_descriptions
# from the previously provided Agent 5 implementation.
