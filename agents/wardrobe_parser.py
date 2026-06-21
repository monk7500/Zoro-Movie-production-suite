"""
Agent 3: Wardrobe & Physical Change Parser
Extracts every character's wardrobe and physical state changes from the screenplay.
Outputs a per‑character timeline that drives Character Visual Designer,
Character Continuity Agent, and Animation Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    tone_analysis = input_slices.get("tone_analysis", {})

    scenes = parsed_script.get("scenes", [])
    characters = parsed_script.get("characters", [])

    if not scenes or not characters:
        empty = {"characters": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "WardrobePhysicalChangeParser",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"wardrobe_timeline.json": final_json.encode("utf-8")}

    # ---- 1. Build a scene‑by‑scene action summary ----
    script_summary = _build_script_summary(scenes, characters)

    # ---- 2. LLM‑based extraction ----
    system_prompt = _build_system_prompt()
    user_prompt = f"Characters: {', '.join(c['name'] for c in characters)}\n\n{script_summary}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=12288
        )
        timeline = _extract_json(response)
    except Exception:
        timeline = _fallback_timeline(scenes, characters)

    # ---- 3. Validate & enforce persistence rules ----
    timeline = _validate_and_enforce_persistence(timeline, scenes, characters)

    # ---- 4. Compute content hash WITHOUT _meta ----
    clean_data = {k: v for k, v in timeline.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # ---- 5. Add metadata ----
    timeline["_meta"] = {
        "agent": "WardrobePhysicalChangeParser",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---- 6. Serialize final output WITH metadata ----
    final_json = json.dumps(timeline, indent=2, ensure_ascii=False)
    return {"wardrobe_timeline.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a continuity script analyst. Extract all wardrobe and physical changes for every character.

For each character, build a "timeline" array of state objects per scene:
{
  "scene": "S01",
  "age": "30" (omit if no time jump),
  "wardrobe": {
    "primary": "leather_jacket",
    "layers": ["black_tank_top"],
    "accessories": ["watch"],
    "condition": "worn, slightly dirty"
  },
  "physical": {
    "injuries": ["cut_forehead"],
    "dirt_level": "none"|"low"|"medium"|"heavy",
    "wetness": "none"|"rain_soaked"|"sweaty",
    "hair_state": "messy, tied back"
  },
  "attached_props": ["backpack"],
  "notes": "Brief explanation of change from previous scene."
}

RULES:
- First appearance MUST have an entry.
- Omit scenes where nothing changes (state persists).
- Injuries / torn clothing persist until explicitly healed / changed.
- Dirt accumulates; can be cleaned by rain / washing / time jump.
- Time jumps → add "age" field.
- Output ONLY valid JSON with top key "characters"."""


def _build_script_summary(scenes: List[dict], characters: List[dict]) -> str:
    parts = []
    for scene in scenes:
        sid = scene.get("id", "?")
        heading = scene.get("heading", "")
        actions = " | ".join(scene.get("action_lines", [])[:4])
        dialogue = " | ".join([
            f"{d.get('character','')}: {d.get('line','')}"
            for d in scene.get("dialogue", [])[:4]
        ])
        parts.append(f"{sid} ({heading}):\n  Actions: {actions}\n  Dialogue: {dialogue}")
    return "\n\n".join(parts)


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


def _fallback_timeline(scenes: List[dict], characters: List[dict]) -> dict:
    timeline = {"characters": {}}
    for char in characters:
        name = char["name"]
        first_scene = char.get("first_appearance", scenes[0]["id"] if scenes else "S01")
        timeline["characters"][name] = {
            "timeline": [{
                "scene": first_scene,
                "wardrobe": {"primary": "unknown", "layers": [], "accessories": [], "condition": "clean"},
                "physical": {"injuries": [], "dirt_level": "none", "wetness": "none", "hair_state": "unknown"},
                "attached_props": [],
                "notes": "Auto‑generated fallback."
            }]
        }
    return timeline


def _validate_and_enforce_persistence(timeline: dict, scenes: List[dict], characters: List[dict]) -> dict:
    timeline.setdefault("characters", {})
    scene_ids = [s["id"] for s in scenes]
    char_names = [c["name"] for c in characters]

    for name in char_names:
        if name not in timeline["characters"]:
            first_scene = next((c.get("first_appearance", "S01") for c in characters if c["name"] == name), scene_ids[0] if scene_ids else "S01")
            timeline["characters"][name] = {"timeline": [_make_default_entry(first_scene)]}
            continue

        char_timeline = timeline["characters"][name].get("timeline", [])
        if not char_timeline:
            first_scene = next((c.get("first_appearance", "S01") for c in characters if c["name"] == name), scene_ids[0] if scene_ids else "S01")
            char_timeline = [_make_default_entry(first_scene)]

        char_timeline.sort(key=lambda e: scene_ids.index(e["scene"]) if e["scene"] in scene_ids else 999)

        filled = []
        current_state = None
        for sid in scene_ids:
            entry = next((e for e in char_timeline if e["scene"] == sid), None)
            if entry:
                entry.setdefault("age", None)
                entry.setdefault("wardrobe", {"primary": "unknown", "layers": [], "accessories": [], "condition": "clean"})
                entry.setdefault("physical", {"injuries": [], "dirt_level": "none", "wetness": "none", "hair_state": "unknown"})
                entry.setdefault("attached_props", [])
                entry.setdefault("notes", "")
                current_state = entry
                filled.append(entry)
            elif current_state:
                carried = {
                    "scene": sid,
                    "age": current_state.get("age"),
                    "wardrobe": current_state["wardrobe"].copy(),
                    "physical": current_state["physical"].copy(),
                    "attached_props": current_state["attached_props"].copy(),
                    "notes": f"State persists from {current_state['scene']}."
                }
                filled.append(carried)

        timeline["characters"][name]["timeline"] = filled

    return timeline


def _make_default_entry(scene_id: str) -> dict:
    return {
        "scene": scene_id,
        "wardrobe": {"primary": "unknown", "layers": [], "accessories": [], "condition": "clean"},
        "physical": {"injuries": [], "dirt_level": "none", "wetness": "none", "hair_state": "unknown"},
        "attached_props": [],
        "notes": "Auto‑generated."
    }
