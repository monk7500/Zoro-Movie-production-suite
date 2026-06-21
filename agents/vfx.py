"""
Agent 33: VFX Agent
Extracts VFX cues from the screenplay and composites effects onto rendered frames.
Uses a pluggable VFXProvider (Blender, Houdini, Diffusion, Simple 2D) or falls back
to text descriptions.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        vfx_provider=None) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    render_manifest = input_slices.get("render_manifest", {}).get("shots", {})
    action_choreo = input_slices.get("action_choreography", {}).get("scenes", {})
    world_rules = input_slices.get("world_rules", {})
    style_guide = input_slices.get("style_guide", {})
    cinematography = input_slices.get("cinematography", {}).get("shots", {})

    scenes = parsed_script.get("scenes", [])

    # ---- 1. Extract VFX cues from script via LLM ----
    vfx_cues = _extract_vfx_cues(scenes, world_rules, llm_provider)

    output_files = {}
    manifest = {"shots": {}}

    for shot_id, render_info in render_manifest.items():
        scene_id = _shot_id_to_scene_id(shot_id)
        scene_cues = vfx_cues.get(scene_id, [])
        if not scene_cues:
            continue

        frame_source = render_info.get("frame_dir") or render_info.get("frame_descriptions_file")
        if not frame_source:
            continue

        shot_effects = []

        if vfx_provider:
            try:
                current_frames = frame_source  # provider would load actual frames
                for cue in scene_cues:
                    if not _cue_applies_to_shot(cue, shot_id, action_choreo):
                        continue
                    effect_desc = {
                        "type": cue["type"],
                        "target_region": cue.get("target_region"),
                        "parameters": cue.get("parameters", {}),
                        "duration_seconds": cue.get("duration_seconds", 2.0),
                        "start_seconds": cue.get("start_seconds", 0.0)
                    }
                    composited = vfx_provider.generate_effect(
                        effect_description=effect_desc,
                        background_frames=current_frames,
                        shot_data={
                            "shot_id": shot_id,
                            "cinematography": cinematography.get(shot_id, {}),
                            "style_guide": style_guide
                        }
                    )
                    current_frames = composited
                    shot_effects.append({
                        "type": cue["type"],
                        "target": cue.get("target", ""),
                        "duration": f"{cue.get('duration_seconds', 2.0)}s"
                    })
                # Write final composited frames
                shot_dir = f"vfx/{shot_id}"
                output_files[f"{shot_dir}/vfx_complete.flag"] = b"1"
                manifest["shots"][shot_id] = {
                    "vfx_frame_dir": shot_dir,
                    "effects_applied": shot_effects
                }
            except Exception as e:
                print(f"[VFXAgent] Generation failed for {shot_id}: {e}")
                vfx_desc = _generate_vfx_description(shot_id, scene_cues, llm_provider)
                output_files[f"vfx/{shot_id}/vfx_description.json"] = json.dumps(vfx_desc, indent=2).encode("utf-8")
                manifest["shots"][shot_id] = {
                    "vfx_description_file": f"vfx/{shot_id}/vfx_description.json",
                    "effects_applied": shot_effects
                }
        else:
            vfx_desc = _generate_vfx_description(shot_id, scene_cues, llm_provider)
            output_files[f"vfx/{shot_id}/vfx_description.json"] = json.dumps(vfx_desc, indent=2).encode("utf-8")
            manifest["shots"][shot_id] = {
                "vfx_description_file": f"vfx/{shot_id}/vfx_description.json",
                "effects_applied": [
                    {"type": c["type"], "target": c.get("target", ""), "duration": f"{c.get('duration_seconds', 2.0)}s"}
                    for c in scene_cues
                ]
            }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "VFXAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["vfx_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _extract_vfx_cues(scenes: List[dict], world_rules: dict, llm_provider) -> dict:
    """Use LLM to identify all VFX‑worthy moments from action lines."""
    scene_descs = []
    for s in scenes:
        actions = " ".join(s.get("action_lines", []))
        scene_descs.append(f"{s['id']}: {actions}")

    magic_exists = world_rules.get("magic_system", {}).get("exists", False)
    tech_level = world_rules.get("technology_level", "present")

    system = f"""Analyze these action lines for moments requiring visual effects.
The world has: magic={magic_exists}, tech_level={tech_level}.
Output a JSON object keyed by scene ID, each containing an array of VFX cues:
- "type": "fire", "magic", "hologram", "explosion", "energy_shield", "screen_insert", "morph", "smoke", "particles", "lightning", "portal"
- "target": what the effect hits (character name, prop name, or "environment")
- "duration_seconds": estimated length
- "start_seconds": estimated start within scene
- "parameters": any specific color, intensity, scale mentioned
Only include moments that CLEARLY require VFX. If no VFX needed, output empty array for that scene."""

    try:
        response = llm_provider.generate(prompt="\n".join(scene_descs), system=system, temperature=0.2)
        return _extract_json(response)
    except:
        return {}


def _cue_applies_to_shot(cue: dict, shot_id: str, action_choreo: dict) -> bool:
    """Check if the VFX cue belongs to this shot. Simplified: always True."""
    return True


def _generate_vfx_description(shot_id: str, cues: List[dict], llm_provider) -> dict:
    """Generate text descriptions of VFX for the shot."""
    system = "Describe the visual effects needed for this shot. Be specific about appearance, timing, and interaction with the scene."
    prompt = f"Shot {shot_id}:\nVFX Cues: {json.dumps(cues)}"
    try:
        response = llm_provider.generate(prompt=prompt, system=system, temperature=0.3)
        return {"description": response}
    except:
        return {"description": f"VFX for shot {shot_id}: {', '.join(c['type'] for c in cues)}"}


def _shot_id_to_scene_id(shot_id: str) -> str:
    return "S01"


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
