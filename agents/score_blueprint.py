"""
Agent 21: Score Blueprint Agent
Generates a detailed musical blueprint from the emotional arc and story beats.
Defines tempo, key, instrumentation, dynamics, and motif usage per scene.
Outputs a structured plan for the Composer Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    tone = input_slices.get("tone_analysis", {})
    parsed_script = input_slices.get("parsed_script", {})
    temp_tracks = input_slices.get("temp_track_refs", [])

    scenes = parsed_script.get("scenes", [])
    global_curve = tone.get("global_curve", [])

    # ---- 1. Build scene‑level summaries with emotional data ----
    scene_summaries = _build_scene_summaries(scenes, global_curve)

    # ---- 2. Build temp track reference description ----
    temp_ref_desc = ""
    if temp_tracks:
        temp_ref_desc = "Reference tracks: " + ", ".join(
            t.get("filename", "unknown") for t in temp_tracks
        )

    # ---- 3. LLM‑based musical blueprint generation ----
    system_prompt = _build_system_prompt()
    user_prompt = f"Emotional curve:\n{scene_summaries}\n{temp_ref_desc}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.4,
            max_tokens=12288
        )
        blueprint = _extract_json(response)
    except Exception:
        blueprint = _fallback_blueprint(global_curve)

    # ---- 4. Validate and fill ----
    blueprint = _validate_and_fill(blueprint, scenes, global_curve)

    # ---- 5. Compute content hash WITHOUT _meta ----
    clean_data = {k: v for k, v in blueprint.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # ---- 6. Add metadata ----
    blueprint["_meta"] = {
        "agent": "ScoreBlueprintAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(blueprint, indent=2, ensure_ascii=False)
    return {"score_blueprint.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a film composer. Create a detailed musical blueprint for the provided scenes as a JSON object.

Include:
- "global": {
    "tempo_bpm": number,
    "key_signature": string (e.g., "D minor"),
    "time_signature": string (e.g., "4/4"),
    "orchestra": array of instruments,
    "main_theme": { "motif_id": string, "description": string, "first_scene": scene ID }
  }
- "scenes": an object keyed by scene ID, each with:
    - "mood": short musical mood description
    - "tempo_override": number or null
    - "dynamics": "pianissimo", "piano", "mezzo-piano", "mezzo-forte", "forte", "fortissimo"
    - "instruments_featured": array of instruments playing in this scene
    - "motif_used": array of motif IDs (can be empty)
    - "notes": any additional direction for the composer

Follow the emotional curve: high arousal → faster tempo, forte; negative valence → minor key; positive valence → major key (or brighter modes). Use leitmotifs for characters or themes. Output ONLY valid JSON."""


def _build_scene_summaries(scenes: List[dict], global_curve: List[dict]) -> str:
    lines = []
    for point in global_curve:
        sid = point.get("scene", "")
        valence = point.get("valence", 0)
        arousal = point.get("arousal", 0)
        # Find matching scene actions
        scene_data = next((s for s in scenes if s["id"] == sid), {})
        actions = " | ".join(scene_data.get("action_lines", [])[:2])
        lines.append(f"{sid}: valence={valence:.1f}, arousal={arousal:.1f}, actions='{actions}'")
    return "\n".join(lines)


def _extract_json(response: str) -> dict:
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


def _fallback_blueprint(global_curve: List[dict]) -> dict:
    blueprint = {
        "global": {
            "tempo_bpm": 90,
            "key_signature": "C major",
            "time_signature": "4/4",
            "orchestra": ["piano"],
            "main_theme": {"motif_id": "main", "description": "simple theme", "first_scene": ""}
        },
        "scenes": {}
    }
    for point in global_curve:
        sid = point.get("scene", "")
        if sid:
            blueprint["scenes"][sid] = {
                "mood": "neutral",
                "tempo_override": None,
                "dynamics": "mezzo-piano",
                "instruments_featured": ["piano"],
                "motif_used": [],
                "notes": "Auto‑generated."
            }
    return blueprint


def _validate_and_fill(blueprint: dict, scenes: List[dict], global_curve: List[dict]) -> dict:
    if "global" not in blueprint:
        blueprint["global"] = {
            "tempo_bpm": 90,
            "key_signature": "C major",
            "time_signature": "4/4",
            "orchestra": ["piano"],
            "main_theme": {"motif_id": "main", "description": "simple theme", "first_scene": ""}
        }
    if "scenes" not in blueprint:
        blueprint["scenes"] = {}

    default_scene = {
        "mood": "neutral",
        "tempo_override": None,
        "dynamics": "mezzo-piano",
        "instruments_featured": ["piano"],
        "motif_used": [],
        "notes": "Auto‑generated."
    }

    for point in global_curve:
        sid = point.get("scene", "")
        if sid and sid not in blueprint["scenes"]:
            blueprint["scenes"][sid] = default_scene.copy()
        elif sid in blueprint["scenes"]:
            for key, val in default_scene.items():
                if key not in blueprint["scenes"][sid]:
                    blueprint["scenes"][sid][key] = val

    return blueprint
