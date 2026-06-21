"""
Agent 35: Lip‑Sync & Audio Alignment Agent
Generates mouth‑synced video frames by compositing lip‑sync data onto graded frames.
Uses a pluggable LipSyncProvider (Wav2Lip, MuseTalk, FaceFormer, SimpleViseme)
or falls back to detailed text descriptions.
"""

import json, hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        lipsync_provider=None) -> Dict[str, bytes]:
    graded = input_slices.get("graded_manifest", {}).get("shots", {})
    voice = input_slices.get("voice_manifest", {}).get("characters", {})
    animation = input_slices.get("animation", {}).get("shots", {})
    dialogue = input_slices.get("dialogue_breakdown", {}).get("scenes", {})
    layout = input_slices.get("layout", {}).get("shots", {})

    output_files = {}
    manifest = {"shots": {}}

    for shot_id, shot_graded in graded.items():
        frame_source = shot_graded.get("graded_frame_dir") or shot_graded.get("grade_description_file")
        if not frame_source:
            continue

        shot_anim = animation.get(shot_id, {})
        characters_in_shot = shot_anim.get("characters_animated", [])
        shot_layout = layout.get(shot_id, {})

        synced_chars = []
        audio_file_used = None
        sync_success = False

        # Only attempt lip‑sync if we have actual frame files (not text descriptions)
        if lipsync_provider and frame_source and not frame_source.endswith(".json"):
            # ---- Obtain sorted list of frame paths ----
            frame_dir = frame_source
            if Path(frame_dir).is_dir():
                frame_paths = sorted(str(p) for p in Path(frame_dir).glob("frame_*.png"))
            else:
                frame_paths = [frame_dir]  # single file or unexpected

            if not frame_paths:
                continue

            for char_name in characters_in_shot:
                # Find if this character speaks in this shot
                audio_path = _get_audio_for_shot_char(shot_id, char_name, voice, dialogue)
                if not audio_path or not isinstance(audio_path, str) or not audio_path.startswith("voice_audio/"):
                    continue

                # Get mouth shape data from animation (if any)
                mouth_data = shot_anim.get("mouth_shapes_file")
                if isinstance(mouth_data, str):
                    mouth_data = _load_mouth_data(mouth_data)

                try:
                    synced_frames = lipsync_provider.sync_shot(
                        video_frames=frame_paths,
                        audio_file=audio_path,
                        mouth_data=mouth_data.get(char_name, {}) if mouth_data else None,
                        shot_context={
                            "shot_id": shot_id,
                            "character_name": char_name,
                            "layout": shot_layout,
                        },
                    )
                    frame_paths = synced_frames  # use synced as new base for next character
                    synced_chars.append(char_name)
                    audio_file_used = audio_path
                    sync_success = True
                except Exception as e:
                    print(f"[LipSync] Sync failed for {char_name} in {shot_id}: {e}")
                    synced_chars.append(f"{char_name} (sync failed)")

            if sync_success:
                shot_dir = f"lipsync/{shot_id}"
                # In a real implementation, save the synced frames to disk.
                # For the cache system, we record the directory.
                # Here we write a flag file as placeholder.
                output_files[f"{shot_dir}/sync_complete.flag"] = b"1"
                manifest["shots"][shot_id] = {
                    "synced_frame_dir": shot_dir,
                    "characters_synced": synced_chars,
                    "audio_file_used": audio_file_used,
                }
        else:
            # ---- Text‑only fallback ----
            desc = _generate_lipsync_description(
                shot_id, characters_in_shot, voice, dialogue, llm_provider
            )
            output_files[f"lipsync/{shot_id}/sync_description.json"] = json.dumps(desc, indent=2).encode("utf-8")
            manifest["shots"][shot_id] = {
                "sync_description_file": f"lipsync/{shot_id}/sync_description.json",
                "characters_synced": characters_in_shot,
            }

    # ---- Metadata fix ----
    clean_manifest = {"shots": manifest["shots"]}
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest["_meta"] = {
        "agent": "LipSyncAudioAlignmentAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }

    output_files["lipsync_manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _get_audio_for_shot_char(
    shot_id: str, char_name: str, voice_manifest: dict, dialogue: dict
) -> Optional[str]:
    """Find the audio file path for a character's line in a shot."""
    char_voice = voice_manifest.get(char_name, {})
    lines = char_voice.get("lines", {})
    for line_id, audio_path in lines.items():
        if _line_in_shot(line_id, shot_id):
            return audio_path
    return None


def _line_in_shot(line_id: str, shot_id: str) -> bool:
    # Simplified: always True. Real implementation would use dialogue breakdown scene mapping.
    return True


def _load_mouth_data(mouth_data_path: str) -> dict:
    # Load from cache. Placeholder.
    return {}


def _generate_lipsync_description(
    shot_id: str, characters: List[str], voice: dict, dialogue: dict, llm_provider
) -> dict:
    """Generate text description of lip‑sync for the shot."""
    system = "Describe the lip‑sync and facial animation for the characters in this shot. Be specific about timing and mouth movements."
    prompt = f"Shot {shot_id}, Characters: {characters}"
    try:
        return {
            "description": llm_provider.generate(
                prompt=prompt, system=system, temperature=0.3
            )
        }
    except:
        return {
            "description": f"Lip‑sync for shot {shot_id} involving {', '.join(characters)}."
    }
