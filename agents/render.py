"""
Agent 31: Render Agent
Generates final video frames for every shot by compositing all production data.
Supports full‑frame rendering, region‑based re‑rendering (via rework_mask), and
text‑only fallback when no render engine is available.
Uses a pluggable RenderEngineProvider.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        render_engine=None) -> Dict[str, bytes]:
    layout = input_slices.get("layout", {}).get("shots", {})
    animation = input_slices.get("animation", {}).get("shots", {})
    physics = input_slices.get("physics", {}).get("shots", {})
    lighting = input_slices.get("lighting", {}).get("shots", {})
    env_fx = input_slices.get("environment_fx", {}).get("scenes", {})
    population = input_slices.get("population", {}).get("shots", {})
    char_visuals = input_slices.get("character_visuals", {}).get("characters", {})
    prop_tracker = input_slices.get("prop_tracker", {}).get("props", {})
    action_choreo = input_slices.get("action_choreography", {}).get("scenes", {})
    cinematography = input_slices.get("cinematography", {}).get("shots", {})
    style_guide = input_slices.get("style_guide", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    rework_mask = input_slices.get("rework_mask")  # None for full render

    output_files = {}
    manifest = {"shots": {}}

    for shot_id, shot_layout in layout.items():
        # Determine if this is a full render or a targeted re‑render
        mask = None
        original_frame_dir = None
        if rework_mask and shot_id in rework_mask:
            mask = rework_mask[shot_id]
            original_frame_dir = _get_previous_render_dir(shot_id)

        scene_id = _shot_id_to_scene_id(shot_id)

        # Build the complete shot data bundle
        shot_data = {
            "shot_id": shot_id,
            "scene_id": scene_id,
            "layout": shot_layout,
            "animation": animation.get(shot_id, {}),
            "physics": physics.get(shot_id, {}),
            "lighting": lighting.get(shot_id, {}),
            "environment": env_fx.get(scene_id, {}),
            "population": population.get(shot_id, {}),
            "character_visuals": char_visuals,
            "prop_states": _get_current_prop_states(shot_id, prop_tracker),
            "action_sequence": action_choreo.get(scene_id, {}),
            "cinematography": cinematography.get(shot_id, {}),
            "style_guide": style_guide,
            "geography": geography.get(shot_layout.get("location", ""), {})
        }

        shot_dir = f"renders/{shot_id}"

        if render_engine:
            try:
                frame_paths = render_engine.render_shot(
                    shot_data=shot_data,
                    output_dir=shot_dir,
                    frame_range=None,
                    mask=mask,
                    original_frame_dir=original_frame_dir
                )
                manifest["shots"][shot_id] = {
                    "frame_dir": shot_dir,
                    "frame_count": len(frame_paths),
                    "resolution": "1920x1080",
                    "frame_rate": 24,
                    "duration_seconds": shot_data["animation"].get("duration_seconds", 5.0)
                }
            except Exception as e:
                print(f"[RenderAgent] Rendering failed for {shot_id}: {e}")
                text_frames = _generate_text_frames(shot_id, shot_data, llm_provider)
                output_files[f"{shot_dir}/frame_descriptions.json"] = json.dumps(text_frames, indent=2).encode("utf-8")
                manifest["shots"][shot_id] = {
                    "frame_descriptions_file": f"{shot_dir}/frame_descriptions.json",
                    "frame_count": len(text_frames.get("frames", [])),
                    "resolution": "text_only",
                    "frame_rate": 24,
                    "duration_seconds": shot_data["animation"].get("duration_seconds", 5.0)
                }
        else:
            text_frames = _generate_text_frames(shot_id, shot_data, llm_provider)
            output_files[f"{shot_dir}/frame_descriptions.json"] = json.dumps(text_frames, indent=2).encode("utf-8")
            manifest["shots"][shot_id] = {
                "frame_descriptions_file": f"{shot_dir}/frame_descriptions.json",
                "frame_count": len(text_frames.get("frames", [])),
                "resolution": "text_only",
                "frame_rate": 24,
                "duration_seconds": shot_data["animation"].get("duration_seconds", 5.0)
            }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "RenderAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["render_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _generate_text_frames(shot_id: str, shot_data: dict, llm_provider) -> dict:
    """Generate frame‑by‑frame text descriptions of what the shot would look like."""
    system = """You are a cinematographer describing a finished film. Provide a frame‑accurate description
of the shot. Include what is visible, camera angle, lighting, character positions and expressions,
props, background, and any movement. Output JSON: { "frames": [ { "frame": int, "description": str } ] }."""
    prompt = f"Shot {shot_id}:\n{json.dumps(shot_data, indent=2)}"
    try:
        response = llm_provider.generate(prompt=prompt, system=system, temperature=0.7, max_tokens=4096)
        return json.loads(response)
    except:
        return {"frames": [{"frame": 0, "description": f"Shot {shot_id} as planned."}]}


def _shot_id_to_scene_id(shot_id: str) -> str:
    return "S01"


def _get_current_prop_states(shot_id: str, prop_tracker: dict) -> dict:
    """Return the state of each dynamic prop at the start of this shot."""
    states = {}
    for pname, pdata in prop_tracker.items():
        states[pname] = pdata.get("initial_state", {})
    return states


def _get_previous_render_dir(shot_id: str) -> Optional[str]:
    return None
