"""
Agent 4: Environment State Agent
Extracts weather, time of day, season, temperature, wind, and special
atmospheric conditions from the screenplay. Produces a per‑scene timeline
that drives Environmental Effects Simulator, Lighting Consistency Agent,
and Atmosphere Continuity Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    scenes = parsed_script.get("scenes", [])

    if not scenes:
        empty = {"scenes": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "EnvironmentStateAgent",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"environment_timeline.json": final_json.encode("utf-8")}

    # ---- 1. Build compact scene list for the LLM ----
    scene_list = _build_scene_list(scenes)

    # ---- 2. LLM‑based environment extraction ----
    system_prompt = _build_system_prompt()
    user_prompt = f"Script:\n{scene_list}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=8192
        )
        env_data = _extract_json(response)
    except Exception:
        env_data = _fallback_environment(scenes)

    # ---- 3. Validate and fill missing scenes ----
    env_data = _validate_and_fill(env_data, scenes)

    # ---- 4. Compute content hash WITHOUT _meta ----
    clean_data = {k: v for k, v in env_data.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # ---- 5. Add metadata ----
    env_data["_meta"] = {
        "agent": "EnvironmentStateAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---- 6. Serialize final output WITH metadata ----
    final_json = json.dumps(env_data, indent=2, ensure_ascii=False)
    return {"environment_timeline.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a script environment analyst. For each scene, determine the environmental conditions.

For each scene ID, provide an object with these EXACT keys:
- "weather": "clear", "rain", "snow", "fog", "storm", "overcast", "drizzle", "windy", "hail", "dust_storm", "sandstorm", "blizzard", "humid", "heatwave", "undefined"
- "time_of_day": "dawn", "morning", "afternoon", "sunset", "dusk", "night", "midnight", "undefined"
- "season": "spring", "summer", "autumn", "winter", "undefined"
- "temperature": "freezing", "cold", "cool", "mild", "warm", "hot", "sweltering", "undefined"
- "wind": "calm", "light_breeze", "windy", "gusty", "gale", "undefined"
- "special_conditions": array of strings (e.g., "flickering neon sign", "smoky room", "dust motes in sunbeams"). Empty array if none.

RULES:
- Infer from scene heading (INT./EXT., time of day) and first few action lines.
- Interior scenes default to calm wind, mild temperature unless action lines say otherwise.
- Exterior scenes: be literal from the heading and action descriptions.
- Do not invent weather that isn't implied.
- Output ONLY valid JSON. Top key must be "scenes"."""


def _build_scene_list(scenes: List[dict]) -> str:
    parts = []
    for scene in scenes:
        sid = scene.get("id", "?")
        heading = scene.get("heading", "")
        actions = " | ".join(scene.get("action_lines", [])[:3])
        parts.append(f"{sid}: {heading} | {actions}")
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


def _fallback_environment(scenes: List[dict]) -> dict:
    env = {"scenes": {}}
    for scene in scenes:
        sid = scene["id"]
        heading = scene.get("heading", "")
        interior = heading.upper().startswith("INT")
        tod = _extract_time_of_day_from_heading(heading)
        env["scenes"][sid] = {
            "weather": "clear",
            "time_of_day": tod,
            "season": "undefined",
            "temperature": "mild" if interior else "cool",
            "wind": "calm" if interior else "light_breeze",
            "special_conditions": []
        }
    return env


def _extract_time_of_day_from_heading(heading: str) -> str:
    match = re.search(r'-\s*(DAY|NIGHT|DAWN|DUSK|MORNING|AFTERNOON|EVENING|MIDNIGHT|SUNSET)', heading, re.IGNORECASE)
    return match.group(1).lower() if match else "day"


def _validate_and_fill(env_data: dict, scenes: List[dict]) -> dict:
    env_data.setdefault("scenes", {})
    default_env = {
        "weather": "clear", "time_of_day": "day", "season": "undefined",
        "temperature": "mild", "wind": "calm", "special_conditions": []
    }
    for scene in scenes:
        sid = scene["id"]
        if sid not in env_data["scenes"]:
            env_data["scenes"][sid] = default_env.copy()
        else:
            for key, val in default_env.items():
                if key not in env_data["scenes"][sid]:
                    env_data["scenes"][sid][key] = val
    return env_data
