"""
Agent 2: Subtext & Tone Analyzer
Reads the parsed script and produces a per‑scene emotional map
(valence, arousal, subtext, pacing) plus a global emotional curve.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    scenes = parsed_script.get("scenes", [])

    if not scenes:
        empty = _empty_tone_analysis()
        return {"tone_analysis.json": json.dumps(empty, indent=2).encode("utf-8")}

    # 1. Build condensed scene summaries for the LLM
    scene_summaries = _build_scene_summaries(scenes)

    # 2. LLM‑based tone analysis
    system_prompt = _build_system_prompt()
    user_prompt = f"Screenplay summary:\n\n{scene_summaries}\n\nAnalyze each scene as instructed."

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=8192
        )
        analysis = _extract_json(response)
    except Exception:
        analysis = _default_tone_analysis(scenes)

    # 3. Validate and fill gaps
    analysis = _validate_and_fill(analysis, scenes)

    # 4. Add metadata
    output_json = json.dumps(analysis, indent=2, ensure_ascii=False)
    analysis["_meta"] = {
        "agent": "SubtextToneAnalyzer",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"tone_analysis.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are an expert script analyst. Analyze the emotional subtext of each scene.

For each scene, provide:
- "primary_emotion": one or two words
- "intensity": 0.0 to 1.0
- "valence": -1.0 (very negative) to 1.0 (very positive)
- "arousal": 0.0 (calm) to 1.0 (excited)
- "subtext": one sentence (or "None.")
- "pacing": "slow", "moderate", or "fast"

Also provide:
- "global_curve": array of {scene, valence, arousal} for each scene, in order
- "dominant_genre_tone": overall mood of the film

Output ONLY valid JSON. Top keys: "scenes", "global_curve", "dominant_genre_tone"."""


def _build_scene_summaries(scenes: List[dict]) -> str:
    parts = []
    for scene in scenes:
        sid = scene.get("id", "?")
        heading = scene.get("heading", "")
        actions = " | ".join(scene.get("action_lines", [])[:3])
        dialogue = " | ".join([
            f"{d.get('character','')}: {d.get('line','')}"
            for d in scene.get("dialogue", [])[:5]
        ])
        parts.append(f"{sid}: {heading}\n  Actions: {actions}\n  Dialogue: {dialogue}")
    return "\n".join(parts)


def _extract_json(response: str) -> dict:
    try: return json.loads(response)
    except: pass
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if fence:
        try: return json.loads(fence.group(1))
        except: pass
    brace = re.search(r'\{[\s\S]*\}', response)
    if brace:
        try: return json.loads(brace.group(0))
        except: pass
    return {}


def _default_tone_analysis(scenes: List[dict]) -> dict:
    scenes_dict = {}
    curve = []
    for i, scene in enumerate(scenes):
        sid = scene.get("id", f"S{i+1:02d}")
        scenes_dict[sid] = {
            "primary_emotion": "neutral", "intensity": 0.3,
            "valence": 0.0, "arousal": 0.2,
            "subtext": "None.", "pacing": "moderate"
        }
        curve.append({"scene": sid, "valence": 0.0, "arousal": 0.2})
    return {"scenes": scenes_dict, "global_curve": curve, "dominant_genre_tone": "neutral"}


def _empty_tone_analysis() -> dict:
    return {"scenes": {}, "global_curve": [], "dominant_genre_tone": "neutral"}


def _validate_and_fill(analysis: dict, scenes: List[dict]) -> dict:
    analysis.setdefault("scenes", {})
    analysis.setdefault("global_curve", [])
    analysis.setdefault("dominant_genre_tone", "neutral")
    for i, scene in enumerate(scenes):
        sid = scene.get("id", f"S{i+1:02d}")
        if sid not in analysis["scenes"]:
            analysis["scenes"][sid] = {
                "primary_emotion": "neutral", "intensity": 0.3,
                "valence": 0.0, "arousal": 0.2,
                "subtext": "None.", "pacing": "moderate"
            }
    curve_ids = {p.get("scene") for p in analysis["global_curve"]}
    for i, scene in enumerate(scenes):
        sid = scene.get("id", f"S{i+1:02d}")
        if sid not in curve_ids:
            sc = analysis["scenes"].get(sid, {})
            analysis["global_curve"].append({
                "scene": sid,
                "valence": sc.get("valence", 0.0),
                "arousal": sc.get("arousal", 0.2)
            })
    return analysis
