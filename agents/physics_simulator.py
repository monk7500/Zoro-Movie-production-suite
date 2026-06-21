"""
Agent 26: Physics Simulator Agent
Generates physically accurate secondary motion: cloth, hair, rigid body collisions,
particles, and fluids. Uses a pluggable PhysicsProvider (Blender, PhysX, Houdini, simple CPU)
or falls back to descriptive physics notes for a human animator.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        physics_provider=None) -> Dict[str, bytes]:
    """
    Args:
        input_slices: {
            "layout": layout.shots,
            "animation": animation.shots,
            "prop_classification": prop_classification.props,
            "geography": geography.locations,
            "character_visuals": character_visuals.characters
        }
        bible_version: current Bible version string
        llm_provider: instance of LLMProvider
        physics_provider: optional instance of PhysicsProvider
    Returns:
        Output files: physics/{shot_id}/physics_cache.json + physics_manifest.json
    """
    layout = input_slices.get("layout", {}).get("shots", {})
    animation = input_slices.get("animation", {}).get("shots", {})
    prop_states = input_slices.get("prop_classification", {}).get("props", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    char_visuals = input_slices.get("character_visuals", {}).get("characters", {})

    output_files = {}
    manifest = {"shots": {}}

    for shot_id, shot_layout in layout.items():
        shot_anim = animation.get(shot_id, {})
        duration = shot_anim.get("duration_seconds", 5.0)
        frame_rate = shot_anim.get("frame_rate", 24)

        # Build scene description for the physics engine
        scene_data = {
            "shot_id": shot_id,
            "entities": shot_layout.get("entities", []),
            "geography": geography.get(shot_layout.get("location", ""), {}),
            "prop_states": prop_states
        }

        if physics_provider:
            try:
                cache = physics_provider.simulate(
                    scene_data=scene_data,
                    animation_data=shot_anim,
                    duration_sec=duration,
                    frame_rate=frame_rate
                )
                shot_dir = f"physics/{shot_id}"
                output_files[f"{shot_dir}/physics_cache.json"] = json.dumps(cache, indent=2).encode("utf-8")

                simulated = []
                if "cloth" in cache:
                    simulated.extend(cache["cloth"].keys())
                if "hair" in cache:
                    simulated.extend(cache["hair"].keys())
                if "rigid_bodies" in cache:
                    simulated.extend([rb["object_id"] for rb in cache["rigid_bodies"]])

                manifest["shots"][shot_id] = {
                    "cache_file": f"{shot_dir}/physics_cache.json",
                    "simulated_entities": simulated,
                    "duration_seconds": duration,
                    "frame_rate": frame_rate
                }
            except Exception as e:
                print(f"[PhysicsSimulator] Simulation failed for {shot_id}: {e}")
                notes = _generate_physics_notes(shot_id, scene_data, shot_anim, llm_provider)
                manifest["shots"][shot_id] = {
                    "physics_notes": notes,
                    "simulated_entities": [],
                    "duration_seconds": duration,
                    "frame_rate": frame_rate
                }
        else:
            notes = _generate_physics_notes(shot_id, scene_data, shot_anim, llm_provider)
            manifest["shots"][shot_id] = {
                "physics_notes": notes,
                "simulated_entities": [],
                "duration_seconds": duration,
                "frame_rate": frame_rate
            }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "PhysicsSimulatorAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["physics_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


def _generate_physics_notes(shot_id: str, scene_data: dict, animation_data: dict, llm_provider) -> str:
    """Generate text notes for a human animator describing the required physics."""
    system = """You are a physics simulation supervisor. Describe all secondary motion and physical interactions
needed for this shot: cloth movement, hair dynamics, rigid body collisions, particles, and any special physics.
Be specific about materials, forces, and timing. Write for a human animator."""
    prompt = f"Shot {shot_id}:\nScene: {json.dumps(scene_data)}\nAnimation: {json.dumps(animation_data)}"
    try:
        return llm_provider.generate(prompt=prompt, system=system, temperature=0.3)
    except:
        return f"Physics notes for shot {shot_id} (auto‑generated)."
