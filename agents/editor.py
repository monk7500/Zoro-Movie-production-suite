"""
Agent 32: Editor Agent
Assembles all rendered shots into a continuous timeline with transitions and audio placement.
Produces an edit timeline (JSON) and optionally a rough cut preview video.
"""

import json, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    render_manifest = input_slices.get("render_manifest", {}).get("shots", {})
    storyboard = input_slices.get("storyboard", {}).get("shots", [])
    cinematography = input_slices.get("cinematography", {}).get("shots", {})
    audio = input_slices.get("audio_manifests", {})
    tone = input_slices.get("tone_analysis", {})

    shots = storyboard
    if not shots:
        # Fallback: use render manifest directly
        shots = [
            {
                "id": sid,
                "scene": sid.replace("SHOT_", "S").split("_")[0] if "_" in sid else "S01",
                "type": "wide",
                "description": f"Shot {sid}",
                "camera": {},
                "characters_in_frame": [],
                "location": "unknown"
            }
            for sid in sorted(render_manifest.keys())
        ]

    timeline = {"tracks": {"video": [], "audio": []}}
    current_time = 0.0

    # ---- 1. Build video track ----
    for i, shot in enumerate(shots):
        shot_id = shot["id"]
        render_info = render_manifest.get(shot_id, {})
        if not render_info:
            duration = 5.0
            frame_dir = None
        else:
            duration = render_info.get("duration_seconds", 5.0)
            frame_dir = render_info.get("frame_dir") or render_info.get("frame_descriptions_file")

        next_shot = shots[i+1] if i+1 < len(shots) else None
        transition_out = None
        transition_in = None
        if i > 0:
            transition_in = "dissolve"
        if next_shot and next_shot.get("scene") != shot.get("scene"):
            transition_out = "dissolve"

        clip = {
            "clip_id": shot_id,
            "source_dir": frame_dir,
            "start_time_seconds": current_time,
            "duration_seconds": duration,
            "transition_in": transition_in,
            "transition_out": transition_out,
            "transition_duration": 0.5
        }
        timeline["tracks"]["video"].append(clip)
        current_time += duration - (0.5 if transition_out else 0)

    # ---- 2. Place audio tracks ----
    ambience = audio.get("ambience", {}).get("scenes", {})
    score = audio.get("score", {}).get("scenes", {})

    for scene_id in _collect_scene_ids(shots):
        scene_start = _get_scene_start_time(scene_id, shots, timeline["tracks"]["video"], render_manifest)
        scene_duration = _get_scene_duration(scene_id, shots, render_manifest)

        # Ambience
        ambience_file = ambience.get(scene_id)
        if ambience_file:
            timeline["tracks"]["audio"].append({
                "clip_id": f"{scene_id}_ambience",
                "source_file": ambience_file if isinstance(ambience_file, str) and ambience_file.startswith("ambience/") else None,
                "source_description": ambience_file if isinstance(ambience_file, str) and not ambience_file.startswith("ambience/") else None,
                "start_time_seconds": scene_start,
                "duration_seconds": scene_duration,
                "volume": 0.3
            })

        # Score
        score_file = score.get(scene_id)
        if score_file:
            timeline["tracks"]["audio"].append({
                "clip_id": f"{scene_id}_score",
                "source_file": score_file if isinstance(score_file, str) and score_file.startswith("score/") else None,
                "source_description": score_file if isinstance(score_file, str) and not score_file.startswith("score/") else None,
                "start_time_seconds": scene_start,
                "duration_seconds": scene_duration,
                "volume": 0.5
            })

    # ---- 3. Place voice and foley ----
    voice = audio.get("voice", {}).get("characters", {})
    foley = audio.get("foley", {}).get("scenes", {})

    for i, shot in enumerate(shots):
        shot_id = shot["id"]
        scene_id = shot.get("scene", "")
        shot_start = timeline["tracks"]["video"][i]["start_time_seconds"]
        shot_duration = timeline["tracks"]["video"][i]["duration_seconds"]

        # Voice lines
        for char_name, char_data in voice.items():
            lines = char_data.get("lines", {})
            for line_id, audio_path in lines.items():
                if _line_in_shot(line_id, shot_id):
                    timeline["tracks"]["audio"].append({
                        "clip_id": line_id,
                        "source_file": audio_path if isinstance(audio_path, str) and audio_path.startswith("voice_audio/") else None,
                        "source_description": audio_path if isinstance(audio_path, str) and not audio_path.startswith("voice_audio/") else None,
                        "start_time_seconds": shot_start,
                        "duration_seconds": shot_duration,
                        "volume": 1.0
                    })

        # Foley
        scene_foley = foley.get(scene_id, [])
        for cue in scene_foley:
            if cue.get("file"):
                timeline["tracks"]["audio"].append({
                    "clip_id": cue.get("sound_id", ""),
                    "source_file": cue["file"],
                    "start_time_seconds": shot_start + cue.get("start_seconds", 0),
                    "duration_seconds": cue.get("duration_seconds", 2.0),
                    "volume": 0.7
                })
            elif cue.get("description"):
                timeline["tracks"]["audio"].append({
                    "clip_id": cue.get("sound_id", ""),
                    "source_description": cue["description"],
                    "start_time_seconds": shot_start + cue.get("start_seconds", 0),
                    "duration_seconds": cue.get("duration_seconds", 2.0),
                    "volume": 0.7
                })

    # ---- 4. Write outputs ----
    output_files = {}
    timeline_json = json.dumps(timeline, indent=2).encode("utf-8")
    output_files["timeline.json"] = timeline_json

    edit_manifest = {
        "timeline_file": "edit/timeline.json",
        "duration_seconds": current_time,
        "shot_count": len(timeline["tracks"]["video"]),
        "output_preview": "edit/rough_cut.mp4"
    }

    # ---- Metadata fix ----
    clean_manifest = {
        "timeline_file": edit_manifest["timeline_file"],
        "duration_seconds": edit_manifest["duration_seconds"],
        "shot_count": edit_manifest["shot_count"],
        "output_preview": edit_manifest["output_preview"]
    }
    content_hash = hashlib.sha256(
        json.dumps(clean_manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    edit_manifest["_meta"] = {
        "agent": "EditorAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    output_files["edit_manifest.json"] = json.dumps(edit_manifest, indent=2).encode("utf-8")
    return output_files


# ---------------------------------------------------------------------------
def _collect_scene_ids(shots: List[dict]) -> List[str]:
    ids = []
    for shot in shots:
        sid = shot.get("scene", "")
        if sid and (not ids or ids[-1] != sid):
            ids.append(sid)
    return ids


def _get_scene_start_time(scene_id: str, shots: List[dict], video_track: List[dict],
                          render_manifest: dict) -> float:
    for clip in video_track:
        for shot in shots:
            if shot["id"] == clip["clip_id"] and shot.get("scene") == scene_id:
                return clip["start_time_seconds"]
    return 0.0


def _get_scene_duration(scene_id: str, shots: List[dict], render_manifest: dict) -> float:
    total = 0.0
    for shot in shots:
        if shot.get("scene") == scene_id:
            total += render_manifest.get(shot["id"], {}).get("duration_seconds", 5.0)
    return total


def _line_in_shot(line_id: str, shot_id: str) -> bool:
    return True
