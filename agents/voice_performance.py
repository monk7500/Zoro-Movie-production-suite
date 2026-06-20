"""
Agent 18: Voice Performance Agent
Generates spoken dialogue audio for every character using a pluggable TTS provider.
Outputs WAV files (or text placeholders) and a manifest mapping each line to its audio file.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider,
        tts_provider=None) -> Dict[str, bytes]:
    """
    Args:
        input_slices: {
            "voice_profiles": voice_profiles.characters,
            "dialogue_scenes": dialogue_breakdown.scenes,
            "character_dialogue_index": dialogue_breakdown.characters
        }
        bible_version: current Bible version string
        llm_provider: instance of LLMProvider (unused here but kept for interface consistency)
        tts_provider: optional instance of TTSProvider
    Returns:
        Output files: voice_audio/{char_name}/{line_id}.wav + voice_manifest.json
    """
    voice_profiles = input_slices.get("voice_profiles", {}).get("characters", {})
    dialogue_scenes = input_slices.get("dialogue_scenes", {})
    char_index = input_slices.get("character_dialogue_index", {})

    output_files = {}
    manifest = {"characters": {}}

    for char_name, char_data in char_index.items():
        profile = voice_profiles.get(char_name, {})
        line_ids = char_data.get("line_ids", [])

        char_manifest = {
            "voice_profile": profile.get("description", "unknown"),
            "lines": {}
        }

        for line_id in line_ids:
            # Find the line in dialogue_scenes
            line_info = _find_line(line_id, dialogue_scenes)
            if not line_info:
                continue

            text = line_info.get("text", "")
            delivery = line_info.get("delivery_notes", {})

            # Generate audio via TTS provider (or text placeholder)
            if tts_provider:
                try:
                    audio_bytes = tts_provider.synthesize(
                        text=text,
                        voice_profile=profile,
                        delivery=delivery
                    )
                    filename = f"voice_audio/{char_name}/{line_id}.wav"
                    output_files[filename] = audio_bytes
                    char_manifest["lines"][line_id] = filename
                except Exception as e:
                    print(f"[VoicePerformance] TTS failed for {line_id} ({char_name}): {e}")
                    placeholder = f"[AUDIO UNAVAILABLE] {char_name}: {text}".encode("utf-8")
                    filename = f"voice_audio/{char_name}/{line_id}_placeholder.txt"
                    output_files[filename] = placeholder
                    char_manifest["lines"][line_id] = filename
            else:
                # No TTS provider – write text file with delivery notes
                text_content = (
                    f"{char_name} ({delivery.get('emotion', 'neutral')}, "
                    f"{delivery.get('pace', 'moderate')}): {text}"
                )
                filename = f"voice_audio/{char_name}/{line_id}.txt"
                output_files[filename] = text_content.encode("utf-8")
                char_manifest["lines"][line_id] = filename

        manifest["characters"][char_name] = char_manifest

    # Add metadata to manifest
    output_json = json.dumps(manifest, indent=2, ensure_ascii=False)
    manifest["_meta"] = {
        "agent": "VoicePerformanceAgent",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["voice_manifest.json"] = output_json.encode("utf-8")
    return output_files


def _find_line(line_id: str, dialogue_scenes: Dict[str, Any]) -> Optional[Dict]:
    """Locate a line's details from the dialogue breakdown scenes."""
    parts = line_id.split("_")
    if len(parts) < 2:
        return None
    scene_id = parts[0]
    scene_data = dialogue_scenes.get(scene_id)
    if not scene_data:
        return None
    for line in scene_data.get("dialogue", []):
        if line.get("line_id") == line_id:
            return line
    return None
