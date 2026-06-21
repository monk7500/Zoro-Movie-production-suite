"""
Agent 8: Anatomical Consultant
Validates character designs against anatomical constraints.
Checks for impossible joint angles, extra/missing digits, proportion errors,
and asymmetry. Uses a pluggable vision provider or falls back to text analysis.
"""

import json, hashlib, math
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        vision_provider=None) -> Dict[str, bytes]:
    character_visuals = input_slices.get("character_visuals", {}).get("characters", {})
    world_rules = input_slices.get("world_rules", {})
    species_rules = world_rules.get("species", {})

    report = {"pass": True, "characters": {}}

    for char_name, char_data in character_visuals.items():
        species = _determine_species(char_name, species_rules)
        constraints = _get_species_constraints(species, species_rules)
        issues = []

        # Check turnaround image if available
        turnaround = char_data.get("base", {}).get("turnaround")
        if turnaround and vision_provider:
            issues.extend(_check_image_anatomy(turnaround, constraints, vision_provider))
        elif turnaround:
            # Text-based fallback using description file
            desc_file = char_data.get("base", {}).get("turnaround_description")
            if desc_file:
                issues.extend(_check_text_anatomy(char_name, desc_file, constraints, llm_provider))

        # Check variant images
        for sig, variant in char_data.get("variants", {}).items():
            img = variant.get("image")
            desc = variant.get("description_file")
            if img and vision_provider:
                issues.extend(_check_image_anatomy(img, constraints, vision_provider))
            elif desc:
                issues.extend(_check_text_anatomy(char_name, desc, constraints, llm_provider))

        report["characters"][char_name] = {
            "pass": len(issues) == 0,
            "issues": issues,
            "species": species
        }
        if issues:
            report["pass"] = False

    # ---- Metadata fix ----
    clean_data = {k: v for k, v in report.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    report["_meta"] = {
        "agent": "AnatomicalConsultant",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(report, indent=2, ensure_ascii=False)
    return {"anatomy_report.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _determine_species(char_name: str, species_rules: dict) -> str:
    """Check if a character matches a non‑human species from world rules."""
    for species_name in species_rules:
        if species_name.lower() in char_name.lower():
            return species_name
    return "human"


def _get_species_constraints(species: str, species_rules: dict) -> dict:
    """Return anatomical constraints for the given species."""
    default_human = {
        "limbs": {"arms": 2, "legs": 2, "fingers_per_hand": 5, "toes_per_foot": 5},
        "joint_limits": {
            "shoulder_abduction": (0, 180),  # degrees
            "elbow_flexion": (0, 145),
            "knee_flexion": (0, 135),
            "hip_abduction": (0, 45),
            "wrist_flexion": (-90, 90),
            "ankle_flexion": (-45, 30)
        },
        "proportions": {"head_to_body_ratio": (1/6, 1/8), "arm_to_height_ratio": (0.35, 0.45)},
        "symmetry_tolerance": 0.05
    }
    if species == "human":
        return default_human
    if species in species_rules:
        custom = species_rules[species].get("anatomy", {})
        merged = default_human.copy()
        if "limbs" in custom:
            merged["limbs"].update(custom["limbs"])
        if "joint_limits" in custom:
            merged["joint_limits"].update(custom["joint_limits"])
        return merged
    return default_human


def _check_image_anatomy(image_path: str, constraints: dict, vision_provider) -> List[dict]:
    """Use a vision model to inspect an image for anatomical issues."""
    system_prompt = f"""Analyze this character image for anatomical errors. Expected anatomy:
Limbs: {constraints.get('limbs', {})}
Joint limits (in degrees): {constraints.get('joint_limits', {})}
Proportions: {constraints.get('proportions', {})}

List any anatomical issues. For each issue, provide:
- "body_part": affected body part
- "problem": short description (e.g., "extra digit", "impossible joint angle", "asymmetry")
- "severity": "critical", "major", or "minor"
- "detail": specific description

If no issues, return an empty array [].
Output ONLY a JSON array."""
    try:
        response = vision_provider.analyze(image_path, system_prompt)
        return json.loads(response)
    except Exception:
        return [{"body_part": "unknown", "problem": "analysis_error", "severity": "minor", "detail": "Vision analysis failed."}]


def _check_text_anatomy(char_name: str, desc_file: str, constraints: dict, llm_provider) -> List[dict]:
    """Use LLM to check a text description for anatomical plausibility."""
    system_prompt = f"""You are an anatomical consultant. Analyze this character description for anatomical errors.
The expected anatomy is:
Limbs: {constraints.get('limbs', {})}
Joint limits (in degrees): {constraints.get('joint_limits', {})}
Proportions: {constraints.get('proportions', {})}

Look for:
- Extra or missing limbs/digits
- Impossible joint positions (e.g., arm bending backward at elbow)
- Severe asymmetry
- Disproportion (e.g., head too large or small for body)

If issues are found, output a JSON array of:
- "body_part": affected part
- "problem": short description
- "severity": "critical", "major", or "minor"
- "detail": explanation

If no issues, output an empty array [].
Output ONLY a JSON array."""
    try:
        response = llm_provider.generate(
            prompt=f"Character: {char_name}\nDescription file: {desc_file}",
            system=system_prompt,
            temperature=0.1
        )
        return json.loads(response)
    except Exception:
        return [{"body_part": "unknown", "problem": "analysis_error", "severity": "minor", "detail": "Text analysis failed."}]
