"""
Agent 22: Composer Agent
Generates the film score from the Score Blueprint using a pluggable MusicProvider.
Produces a main theme audio file and per‑scene score stems (WAV), or falls back
to detailed text musical descriptions.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        music_provider=None) -> Dict[str, bytes]:
    """
    Args:
        input_slices: {
            "score_blueprint": score_blueprint,
            "tone_analysis": tone_analysis,
            "parsed_script": parsed_script
        }
        bible_version: current Bible version string
        llm_provider: instance of LLMProvider (unused here but kept for interface consistency)
        music_provider: optional instance of MusicProvider
    Returns:
        Output files: score/main_theme.wav, score/{scene_id}_score.wav + score_manifest.json
    """
    blueprint = input_slices["score_blueprint"]
    tone = input_slices.get("tone_analysis", {})
    parsed_script = input_slices.get("parsed_script", {})

    global_bp = blueprint.get("global", {})
    scenes_bp = blueprint.get("scenes", {})

    output_files = {}
    manifest = {"global": {}, "scenes": {}}

    # ---- 1. Generate Main Theme ----
    main_theme = global_bp.get("main_theme", {})
    if main_theme and music_provider:
        motif_desc = main_theme.get("description", "main theme")
        key = global_bp.get("key_signature", "C minor")
        tempo = global_bp.get("tempo_bpm", 90)
        orch = global_bp.get("orchestra", ["piano"])
        prompt = f"{motif_desc}, {key}, {tempo} bpm, instruments: {', '.join(orch)}"

        try:
            theme_audio = music_provider.generate(
                prompt=prompt,
                duration_seconds=30.0,
                key=key,
                tempo_bpm=tempo,
                instruments=orch
            )
            output_files["score/main_theme.wav"] = theme_audio
            manifest["global"]["main_theme"] = "score/main_theme.wav"
        except Exception as e:
            print(f"[Composer] Main theme generation failed: {e}")
            manifest["global"]["main_theme"] = f"[AUDIO UNAVAILABLE] {prompt}"
    elif main_theme and not music_provider:
        manifest["global"]["main_theme"] = (
            f"Main theme: {main_theme.get('description', '')}, "
            f"key: {global_bp.get('key_signature', 'C minor')}, "
            f"tempo: {global_bp.get('tempo_bpm', 90)} bpm, "
            f"instruments: {', '.join(global_bp.get('orchestra', ['piano']))}"
        )

    # ---- 2. Generate Per‑Scene Score ----
    for scene_id, scene_bp in scenes_bp.items():
        mood = scene_bp.get("mood", "neutral")
        tempo = scene_bp.get("tempo_override") or global_bp.get("tempo_bpm", 90)
        dynamics = scene_bp.get("dynamics", "mezzo-piano")
        instruments = scene_bp.get("instruments_featured", global_bp.get("orchestra", ["piano"]))
        motifs = ", ".join(scene_bp.get("motif_used", []))
        notes = scene_bp.get("notes", "")
        key = global_bp.get("key_signature", "C minor")

        prompt = (
            f"{mood}, {dynamics}, {tempo} bpm, {key}, "
            f"instruments: {', '.join(instruments)}"
        )
        if motifs:
            prompt += f", using motif: {motifs}"
        if notes:
            prompt += f", {notes}"

        # Estimate scene duration
        duration = _estimate_scene_duration(scene_id, parsed_script)

        if music_provider:
            try:
                audio = music_provider.generate(
                    prompt=prompt,
                    duration_seconds=duration,
                    key=key,
                    tempo_bpm=tempo,
                    instruments=instruments
                )
                filename = f"score/{scene_id}_score.wav"
                output_files[filename] = audio
                manifest["scenes"][scene_id] = filename
            except Exception as e:
                print(f"[Composer] Score generation failed for {scene_id}: {e}")
                manifest["scenes"][scene_id] = f"[AUDIO UNAVAILABLE] {prompt}"
        else:
            manifest["scenes"][scene_id] = prompt

    # ---- Metadata fix ----
    clean_manifest = {"global": manifest["global"], "scenes": manifest["scenes"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "ComposerAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["score_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _estimate_scene_duration(scene_id: str, parsed_script: dict) -> float:
    """Rough estimate: count dialogue + action lines, assume ~5 seconds each."""
    scenes = parsed_script.get("scenes", [])
    for scene in scenes:
        if scene.get("id") == scene_id:
            line_count = len(scene.get("dialogue", [])) + len(scene.get("action_lines", []))
            return max(10.0, line_count * 5.0)
    return 30.0
