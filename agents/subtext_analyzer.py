"""
Agent 2: Subtext & Tone Analyzer
Reads the parsed screenplay and outputs a per‑scene emotional map
(valence/arousal), subtext, pacing, and a global emotional curve.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    scenes = parsed_script.get("scenes", [])

    if not scenes:
        empty = _empty_tone_analysis()
        # Metadata for empty case
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "SubtextToneAnalyzer",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"tone_analysis.json": final_json.encode("utf-8")}

    # ---- 1. Build condensed scene summaries for the LLM ----
    scene_summaries = _build_scene_summaries(scenes)

    # ---- 2. LLM‑based tone analysis ----
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

    # ---- 3. Validate and fill gaps ----
    analysis = _validate_and_fill(analysis, scenes)

    # ---- 4. Compute content hash WITHOUT _meta ----
    clean_data = {k: v for k, v in analysis.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # ---- 5. Add metadata ----
    analysis["_meta"] = {
        "agent": "SubtextToneAnalyzer",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---- 6. Serialize final output WITH metadata ----
    final_json = json.dumps(analysis, indent=2, ensure_ascii=False)
    return {"tone_analysis.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are an expert script analyst. Analyze the emotional subtext of each scene.

For each scene, provide:
- "primary_emotion": one or two words (e.g., "quiet despair", "explosive rage", "hopeful tension")
- "intensity": 0.0 (almost imperceptible) to 1.0 (overwhelming)
- "valence": -1.0 (very negative) to 1.0 (very positive). Think of it as pleasantness/unpleasantness.
- "arousal": 0.0 (very calm) to 1.0 (very agitated/excited)
- "subtext": one sentence explaining what is really happening beneath the surface. If there is no subtext, say "None."
- "pacing": "slow", "moderate", or "fast"

Also provide:
- "global_curve": an array of the same valence/arousal values for each scene, in scene order.
- "dominant_genre_tone": overall mood of the film (e.g., "neo-noir melancholic", "action thriller tense").

Output ONLY valid JSON. No markdown. The top-level keys must be: "scenes", "global_curve", "dominant_genre_tone".
The "scenes" key contains an object mapping scene IDs to their analysis objects."""


# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
def _extract_json(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    # Try markdown fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    # Try first { ... } block
    brace_match = re.search(r'\{[\s\S]*\}', response)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


# ---------------------------------------------------------------------------
def _default_tone_analysis(scenes: List[dict]) -> dict:
    scenes_dict = {}
    curve = []
    for scene in scenes:
        sid = scene.get("id", f"S{scenes.index(scene)+1:02d}")
        scenes_dict[sid] = {
            "primary_emotion": "neutral",
            "intensity": 0.3,
            "valence": 0.0,
            "arousal": 0.2,
            "subtext": "None.",
            "pacing": "moderate"
        }
        curve.append({"scene": sid, "valence": 0.0, "arousal": 0.2})
    return {
        "scenes": scenes_dict,
        "global_curve": curve,
        "dominant_genre_tone": "neutral"
    }


# ---------------------------------------------------------------------------
def _empty_tone_analysis() -> dict:
    return {
        "scenes": {},
        "global_curve": [],
        "dominant_genre_tone": "neutral"
    }


# ---------------------------------------------------------------------------
def _validate_and_fill(analysis: dict, scenes: List[dict]) -> dict:
    if "scenes" not in analysis or not isinstance(analysis["scenes"], dict):
        analysis["scenes"] = {}
    for scene in scenes:
        sid = scene.get("id", f"S{scenes.index(scene)+1:02d}")
        if sid not in analysis["scenes"]:
            analysis["scenes"][sid] = {
                "primary_emotion": "neutral",
                "intensity": 0.3,
                "valence": 0.0,
                "arousal": 0.2,
                "subtext": "None.",
                "pacing": "moderate"
            }

    # Ensure global curve exists and covers all scenes
    if "global_curve" not in analysis or not isinstance(analysis["global_curve"], list):
        analysis["global_curve"] = []
    existing_scenes_in_curve = {pt.get("scene") for pt in analysis["global_curve"]}
    for scene in scenes:
        sid = scene.get("id", "")
        if sid not in existing_scenes_in_curve:
            sc = analysis["scenes"].get(sid, {})
            analysis["global_curve"].append({
                "scene": sid,
                "valence": sc.get("valence", 0.0),
                "arousal": sc.get("arousal", 0.2)
            })

    if "dominant_genre_tone" not in analysis:
        analysis["dominant_genre_tone"] = "neutral"

    return analysis
