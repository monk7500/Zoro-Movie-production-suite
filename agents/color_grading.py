"""
Agent 34: Color Grading Agent
Applies the final color grade to every frame based on the locked Style Guide.
Uses a pluggable ColorGradingProvider (LUT, neural, or simple OpenCV), or falls back
to detailed text descriptions. A style guide change only re‑grades; nothing is re‑rendered.
"""

import json, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        color_provider=None) -> Dict[str, bytes]:
    vfx_shots = input_slices.get("vfx_manifest", {}).get("shots", {})
    render_shots = input_slices.get("render_manifest", {}).get("shots", {})
    style_guide = input_slices.get("style_guide", {})
    cinematography = input_slices.get("cinematography", {}).get("shots", {})

    # ---- 1. Build global grade parameters from style guide ----
    post = style_guide.get("post_processing", {})
    palette = style_guide.get("color_palette", {})
    global_grade = {
        "lut_file": post.get("lut_file"),
        "dominant_colors": palette.get("dominant", []),
        "accent_colors": palette.get("accent", []),
        "mood": palette.get("mood", ""),
        "grain": post.get("grain", "none"),
        "vignette": post.get("vignette", "none"),
        "halation": post.get("halation", "none"),
        "saturation": post.get("saturation", 1.0),
        "contrast": post.get("contrast", 1.0),
    }

    output_files = {}
    manifest = {"shots": {}}

    # Collect all shots: VFX takes priority over base renders
    all_shots = {}
    all_shots.update(render_shots)
    all_shots.update(vfx_shots)

    for shot_id, shot_info in all_shots.items():
        # Determine source frames (directory of images or text description)
        frame_dir = shot_info.get("vfx_frame_dir") or shot_info.get("frame_dir")
        frame_desc = shot_info.get("vfx_description_file") or shot_info.get(
            "frame_descriptions_file"
        )

        # ---- Merge global grade with any per‑shot overrides ----
        cine = cinematography.get(shot_id, {})
        shot_grade = global_grade.copy()
        # Override from cinematography lighting notes or explicit color overrides
        overrides = cine.get("color_grade_overrides", {})
        if overrides:
            shot_grade.update(overrides)

        if color_provider and frame_dir:
            # ---- Obtain sorted list of frame paths ----
            frame_paths = sorted(
                str(p) for p in Path(frame_dir).glob("frame_*.png")
            )
            if not frame_paths:
                # If directory exists but no frames found, fall back to text
                desc = _generate_grade_description(shot_id, shot_grade, llm_provider)
                output_files[
                    f"graded/{shot_id}/grade_description.json"
                ] = json.dumps(desc, indent=2).encode("utf-8")
                manifest["shots"][shot_id] = {
                    "grade_description_file": f"graded/{shot_id}/grade_description.json"
                }
                continue

            try:
                graded_dir = color_provider.apply_grade(
                    frame_paths=frame_paths,
                    grade_params=shot_grade,
                    output_dir=f"graded/{shot_id}",
                )
                manifest["shots"][shot_id] = {
                    "graded_frame_dir": graded_dir,
                    "grade_params_used": {
                        "lut": shot_grade.get("lut_file"),
                        "grain": shot_grade.get("grain"),
                        "vignette": shot_grade.get("vignette"),
                    },
                }
            except Exception as e:
                print(f"[ColorGrading] Grade failed for {shot_id}: {e}")
                desc = _generate_grade_description(shot_id, shot_grade, llm_provider)
                output_files[
                    f"graded/{shot_id}/grade_description.json"
                ] = json.dumps(desc, indent=2).encode("utf-8")
                manifest["shots"][shot_id] = {
                    "grade_description_file": f"graded/{shot_id}/grade_description.json"
                }
        else:
            # Text‑only fallback (no provider or no frame directory)
            desc = _generate_grade_description(shot_id, shot_grade, llm_provider)
            output_files[
                f"graded/{shot_id}/grade_description.json"
            ] = json.dumps(desc, indent=2).encode("utf-8")
            manifest["shots"][shot_id] = {
                "grade_description_file": f"graded/{shot_id}/grade_description.json"
            }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "ColorGradingAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }

    output_files["grade_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


def _generate_grade_description(
    shot_id: str, grade_params: dict, llm_provider
) -> dict:
    """Generate a text description of the intended color grade."""
    system = "You are a colorist. Describe the final color grade for this shot based on the provided parameters."
    prompt = f"Shot {shot_id}:\nGrade params: {json.dumps(grade_params)}"
    try:
        return {
            "description": llm_provider.generate(
                prompt=prompt, system=system, temperature=0.3
            )
        }
    except:
        return {
            "description": f"Color grade for shot {shot_id}: {grade_params.get('mood', 'neutral')}"
            }
