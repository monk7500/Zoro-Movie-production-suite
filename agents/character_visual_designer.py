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
    """
    Args:
        input_slices: {
            "characters": parsed_script.characters,
            "wardrobe_timeline": wardrobe_timeline.characters,
            "style_guide": style_guide,
            "tone_analysis": tone_analysis
        }
        bible_version: current Bible version string
        llm_provider: instance of LLMProvider
        image_provider: optional instance of ImageProvider
    Returns:
        Output files: character_visuals/{name}/... + manifest.json
    """
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

        # Collect unique physical states from wardrobe timeline
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

    output_files["manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _collect_unique_states(timeline: List[dict], base_description: str) -> List[dict]:
    """Extract unique (outfit, physical, age) combinations from timeline."""
    seen = {}
    for entry in timeline:
        outfit = entry.get("wardrobe", {})
        physical = entry.get("physical", {})
        age = entry.get("age")
        scene = entry.get("scene", "?")

        outfit_key = outfit.get("primary", "unknown")
        phys_key = json.dumps({
            "injuries": sorted(physical.get("injuries", [])),
            "dirt": physical.get("dirt_level", "none"),
            "wetness": physical.get("wetness", "none"),
            "hair": physical.get("hair_state", "unknown"),
            "age": age
        }, sort_keys=True)
        signature = hashlib.sha256(f"{outfit_key}|{phys_key}".encode()).hexdigest()[:12]

        if signature not in seen:
            seen[signature] = {
                "signature": signature,
                "outfit": outfit,
                "physical": physical,
                "age": age,
                "scenes": [scene],
                "base_description": base_description
            }
        else:
            seen[signature]["scenes"].append(scene)

    return list(seen.values())


# ---------------------------------------------------------------------------
def _generate_images(provider, name: str, base_desc: str, states: List[dict],
                     palette_mood: str, lighting_mood: str,
                     output_files: Dict[str, bytes]) -> dict:
    """Generate actual PNG images via the image provider."""

    # 1. Base turnaround
    prompt = (
        f"Full-body turnaround character sheet of {name}, {base_desc}, "
        f"three views: front, side, back, neutral pose, standing, "
        f"style: {palette_mood}, lighting: {lighting_mood}, "
        f"high detail, concept art, consistent face and body across all views"
    )
    try:
        img = provider.generate(prompt=prompt, negative="deformed, extra limbs, blurry, inconsistent", width=1024, height=1024, seed=42)
        output_files[f"{name}/turnaround_base.png"] = img
    except Exception:
        output_files[f"{name}/turnaround_base_error.txt"] = f"Image generation failed for {name} turnaround.".encode()

    # 2. Face reference sheet
    prompt = (
        f"Close-up face reference sheet of {name}, {base_desc}, "
        f"neutral expression, front view and profile, "
        f"style: {palette_mood}, high detail, concept art"
    )
    try:
        img = provider.generate(prompt=prompt, negative="deformed, different face, asymmetrical", width=1024, height=1024, seed=42)
        output_files[f"{name}/face_sheet.png"] = img
    except Exception:
        output_files[f"{name}/face_sheet_error.txt"] = f"Image generation failed for {name} face sheet.".encode()

    # 3. Outfit and state variants
    outfits_manifest = {}
    variants_manifest = {}
    for state in states:
        outfit_label = state["outfit"].get("primary", "default")
        sig = state["signature"]
        age_str = f"{state['age']} years old" if state.get("age") else ""
        injuries = ", ".join(state["physical"].get("injuries", []))
        dirt = state["physical"].get("dirt_level", "")
        wetness = state["physical"].get("wetness", "")
        hair = state["physical"].get("hair_state", "")

        # Outfit variant (once per unique outfit)
        if outfit_label not in outfits_manifest:
            prompt = (
                f"{name} wearing {outfit_label.replace('_', ' ')}, {base_desc}, "
                f"full-body, front view, standing, "
                f"style: {palette_mood}, lighting: {lighting_mood}, "
                f"consistent with face reference, concept art"
            )
            try:
                img = provider.generate(prompt=prompt, negative="deformed, different face, inconsistent", width=1024, height=1024, seed=42)
                fname = f"{name}/outfit_{outfit_label}.png"
                output_files[fname] = img
                outfits_manifest[outfit_label] = {"image": fname}
            except Exception:
                outfits_manifest[outfit_label] = {"error": f"Failed for {outfit_label}"}

        # State‑specific variant
        prompt = (
            f"{name}, {age_str}, wearing {outfit_label.replace('_', ' ')}, "
            f"{injuries}, {dirt} dirt, {wetness}, {hair}, "
            f"full-body, front view, consistent with reference face, "
            f"style: {palette_mood}, cinematic lighting, high detail"
        )
        try:
            img = provider.generate(prompt=prompt, negative="deformed, different face, inconsistent", width=1024, height=1024, seed=42)
            fname = f"{name}/variant_{sig}.png"
            output_files[fname] = img
            variants_manifest[sig] = {
                "signature": {"outfit": outfit_label, "age": state.get("age"),
                              "injuries": state["physical"].get("injuries", []),
                              "dirt": dirt, "wetness": wetness, "hair": hair},
                "image": fname,
                "scenes": state["scenes"]
            }
        except Exception:
            variants_manifest[sig] = {
                "signature": {"outfit": outfit_label, "age": state.get("age"),
                              "injuries": state["physical"].get("injuries", []),
                              "dirt": dirt, "wetness": wetness, "hair": hair},
                "error": f"Failed for variant {sig}",
                "scenes": state["scenes"]
            }

    return {
        "base": {"turnaround": f"{name}/turnaround_base.png", "face_sheet": f"{name}/face_sheet.png"},
        "outfits": outfits_manifest,
        "variants": variants_manifest
    }


# ---------------------------------------------------------------------------
def _generate_text_descriptions(llm_provider, name: str, base_desc: str,
                                states: List[dict], palette_mood: str,
                                lighting_mood: str,
                                output_files: Dict[str, bytes]) -> dict:
    """Fallback: generate detailed text descriptions via the LLM."""
    system = f"""You are a concept artist. Describe the character {name} in extreme visual detail.
Base description from script: {base_desc}
Style: {palette_mood}, Lighting: {lighting_mood}
For each state requested, provide a vivid, production‑ready visual description."""

    # Turnaround description
    try:
        resp = llm_provider.generate(
            prompt=f"Describe a full‑body turnaround character sheet of {name} (front, side, back view).",
            system=system, temperature=0.7
        )
        output_files[f"{name}/turnaround_description.txt"] = resp.encode("utf-8")
    except Exception:
        output_files[f"{name}/turnaround_description.txt"] = f"Turnaround of {name}: {base_desc}".encode()

    # Face sheet description
    try:
        resp = llm_provider.generate(
            prompt=f"Describe a close‑up face reference sheet of {name} (front and profile views).",
            system=system, temperature=0.7
        )
        output_files[f"{name}/face_sheet_description.txt"] = resp.encode("utf-8")
    except Exception:
        output_files[f"{name}/face_sheet_description.txt"] = f"Face of {name}: {base_desc}".encode()

    outfits_manifest = {}
    variants_manifest = {}
    for state in states:
        outfit_label = state["outfit"].get("primary", "default")
        sig = state["signature"]
        age_str = f"{state['age']} years old" if state.get("age") else ""
        injuries = ", ".join(state["physical"].get("injuries", []))
        dirt = state["physical"].get("dirt_level", "")
        wetness = state["physical"].get("wetness", "")
        hair = state["physical"].get("hair_state", "")

        if outfit_label not in outfits_manifest:
            try:
                resp = llm_provider.generate(
                    prompt=f"Describe {name} wearing {outfit_label.replace('_', ' ')} in full‑body front view.",
                    system=system, temperature=0.7
                )
                fname = f"{name}/outfit_{outfit_label}_description.txt"
                output_files[fname] = resp.encode("utf-8")
                outfits_manifest[outfit_label] = {"description_file": fname}
            except Exception:
                outfits_manifest[outfit_label] = {"error": f"Failed for {outfit_label}"}

        try:
            resp = llm_provider.generate(
                prompt=f"Describe {name}, {age_str}, wearing {outfit_label.replace('_', ' ')}, "
                       f"with {injuries}, {dirt} dirt, {wetness}, {hair}. Full‑body front view.",
                system=system, temperature=0.7
            )
            fname = f"{name}/variant_{sig}_description.txt"
            output_files[fname] = resp.encode("utf-8")
            variants_manifest[sig] = {
                "signature": {"outfit": outfit_label, "age": state.get("age"),
                              "injuries": state["physical"].get("injuries", []),
                              "dirt": dirt, "wetness": wetness, "hair": hair},
                "description_file": fname,
                "scenes": state["scenes"]
            }
        except Exception:
            variants_manifest[sig] = {
                "signature": {"outfit": outfit_label, "age": state.get("age"),
                              "injuries": state["physical"].get("injuries", []),
                              "dirt": dirt, "wetness": wetness, "hair": hair},
                "error": f"Failed for variant {sig}",
                "scenes": state["scenes"]
            }

    return {
        "base": {
            "turnaround_description": f"{name}/turnaround_description.txt",
            "face_sheet_description": f"{name}/face_sheet_description.txt"
        },
        "outfits": outfits_manifest,
        "variants": variants_manifest
    }
