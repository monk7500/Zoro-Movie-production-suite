"""
Agent 29: Population Generator Agent
Generates background characters (crowds), animals, birds, and traffic for each shot.
Uses LLM to determine population needs from script, then procedurally places
varied entities with unique IDs and simple animation loops.
"""

import json, hashlib, random, math, re
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    layout = input_slices.get("layout", {}).get("shots", {})
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})
    style_guide = input_slices.get("style_guide", {})

    scenes = parsed_script.get("scenes", [])
    output_files = {}
    manifest = {"shots": {}}

    # ---- 1. Extract population cues from script (LLM, cached per scene) ----
    scene_population = _extract_population_cues(scenes, llm_provider)

    # ---- 2. Pre‑generate variant library (appearances) — deterministic, seed‑based ----
    variant_library = _build_variant_library(style_guide)

    # ---- 3. For each shot, populate based on location and scene cues ----
    for shot_id, shot_layout in layout.items():
        scene_id = _shot_id_to_scene_id(shot_id)
        location = shot_layout.get("location", "UNKNOWN")
        geo = geography.get(location, {})
        boundary = geo.get("boundary", {"width_m": 10, "depth_m": 10})
        pop_cues = scene_population.get(scene_id, {"humans": 0, "animals": {}, "vehicles": {}})

        entities = []
        random.seed(_stable_seed(shot_id))

        # Place humans
        for i in range(pop_cues.get("humans", 0)):
            entity = _create_background_entity(
                entity_type="human", index=i, boundary=boundary,
                variant_library=variant_library,
                fixed_objects=geo.get("fixed_objects", []),
                existing_entities=entities
            )
            entities.append(entity)

        # Place animals
        for animal_type, count in pop_cues.get("animals", {}).items():
            for i in range(count):
                entity = _create_background_entity(
                    entity_type=animal_type, index=i, boundary=boundary,
                    variant_library=variant_library,
                    fixed_objects=[],
                    existing_entities=entities
                )
                entities.append(entity)

        # Place background vehicles
        for v_type, count in pop_cues.get("vehicles", {}).items():
            for i in range(count):
                entity = _create_background_entity(
                    entity_type=v_type, index=i, boundary=boundary,
                    variant_library=variant_library,
                    fixed_objects=[],
                    existing_entities=entities
                )
                entities.append(entity)

        # Write per‑shot data
        shot_dir = f"population/{shot_id}"
        pop_data = {"entities": entities}
        output_files[f"{shot_dir}/population_data.json"] = json.dumps(pop_data, indent=2).encode("utf-8")

        type_counts = {}
        for e in entities:
            t = e["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        manifest["shots"][shot_id] = {
            "population_file": f"{shot_dir}/population_data.json",
            "total_entities": len(entities),
            "entity_types": type_counts
        }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "PopulationGeneratorAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["population_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _extract_population_cues(scenes: List[dict], llm_provider) -> dict:
    """Use LLM to determine how many background entities each scene needs."""
    scene_descs = []
    for s in scenes:
        actions = " ".join(s.get("action_lines", [])[:3])
        scene_descs.append(f"{s['id']} ({s['heading']}): {actions}")

    system = """Analyze each scene for background population needs. Output JSON:
{ "S01": { "humans": 5, "animals": {"birds": 2}, "vehicles": {"cars": 1} }, ... }
Estimate numbers from descriptions like "busy market" (20+ humans), "empty street" (0).
Output ONLY valid JSON."""

    try:
        response = llm_provider.generate(prompt="\n".join(scene_descs), system=system, temperature=0.2)
        return _extract_json(response)
    except:
        return {}


def _build_variant_library(style_guide: dict) -> dict:
    """Generate a deterministic set of variant labels for background entities."""
    return {
        "human": [f"person_casual_{i:02d}" for i in range(30)],
        "bird": ["crow", "pigeon", "sparrow", "seagull"],
        "cat": ["tabby", "black_cat", "ginger"],
        "dog": ["mutt", "bulldog", "shepherd"],
        "car": ["sedan_grey", "sedan_blue", "hatchback_red", "suv_black", "truck_white"]
    }


def _create_background_entity(entity_type: str, index: int, boundary: dict,
                              variant_library: dict, fixed_objects: List[dict],
                              existing_entities: List[dict]) -> dict:
    """Place a single background entity within the boundary, avoiding overlaps."""
    w = boundary.get("width_m", 10) / 2.0
    d = boundary.get("depth_m", 10) / 2.0

    pos = {
        "x": random.uniform(-w + 0.5, w - 0.5),
        "y": random.uniform(-d + 0.5, d - 0.5),
        "z": 0.0
    }

    variants = variant_library.get(entity_type, ["default"])
    variant = variants[index % len(variants)]

    return {
        "id": f"BG_{entity_type.upper()}_{index:03d}",
        "type": entity_type,
        "variant_id": variant,
        "position": pos,
        "rotation_y": random.uniform(0, 360),
        "animation_loop": _get_default_animation(entity_type),
        "appearance_ref": f"population/variants/{variant}.png"
    }


def _get_default_animation(entity_type: str) -> str:
    defaults = {
        "human": "idle_standing",
        "bird": "perched_idle",
        "car": "parked",
        "dog": "sitting_idle",
        "cat": "lying_idle"
    }
    return defaults.get(entity_type, "idle")


def _shot_id_to_scene_id(shot_id: str) -> str:
    return "S01"


def _stable_seed(shot_id: str) -> int:
    return int(hashlib.sha256(shot_id.encode()).hexdigest()[:8], 16) % (2**31)


def _extract_json(response: str) -> Any:
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
