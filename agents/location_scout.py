"""
Agent 9: Location Scout Agent
Generates a detailed profile for every unique location in the screenplay:
dimensions, materials, lighting, ambience, era, props, and special features.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    scenes = input_slices.get("scenes", [])
    env_timeline = input_slices.get("environment_timeline", {}).get("scenes", {})

    if not scenes:
        empty = {"locations": {}}
        return {"location_profiles.json": json.dumps(empty, indent=2).encode("utf-8")}

    # 1. Collect unique locations and their first appearances
    location_map = _collect_unique_locations(scenes, env_timeline)

    # 2. Build summaries for the LLM
    location_summaries = _build_location_summaries(location_map)

    # 3. LLM‑based location profiling
    system_prompt = _build_system_prompt()
    user_prompt = f"Location summaries:\n{location_summaries}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=12288
        )
        profiles = _extract_json(response)
    except Exception:
        profiles = _fallback_profiles(location_map)

    # 4. Validate and fill missing locations
    profiles = _validate_and_fill(profiles, location_map)

    # 5. Add metadata
    output_json = json.dumps(profiles, indent=2, ensure_ascii=False)
    profiles["_meta"] = {
        "agent": "LocationScoutAgent",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"location_profiles.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a location scout and production designer. For each location, generate a detailed profile as JSON.

For each location, include these EXACT keys:
- "description": a vivid, visual description of the space (2-3 sentences).
- "dimensions": approximate size (e.g., "12m x 8m" or "small booth"). Use "unknown" if unclear.
- "materials": array of major surface materials (e.g., ["worn_wood", "mahogany", "neon_glass"]).
- "lighting": description of natural and practical light sources present.
- "ambience": atmospheric sounds and mood.
- "era": time period if inferable, otherwise "present".
- "props": array of key objects that define the space.
- "special_features": array of unique architectural or decorative details.

Base output SOLELY on the script information provided. Do not invent unrelated details.
Output ONLY valid JSON. Top key must be "locations"."""


def _collect_unique_locations(scenes: List[dict], env_timeline: dict) -> dict:
    location_map = {}
    for scene in scenes:
        loc = scene.get("location", "UNKNOWN").upper().strip() or "UNKNOWN"
        if loc not in location_map:
            heading = scene.get("heading", "")
            actions = " ".join(scene.get("action_lines", [])[:3])
            env = env_timeline.get(scene["id"], {})
            location_map[loc] = {
                "heading": heading,
                "first_actions": actions,
                "default_weather": env.get("weather", "clear"),
                "default_time": env.get("time_of_day", "day"),
                "scene_ids": [scene["id"]]
            }
        else:
            location_map[loc]["scene_ids"].append(scene["id"])
    return location_map


def _build_location_summaries(location_map: dict) -> str:
    parts = []
    for loc, info in location_map.items():
        parts.append(
            f"{loc}: heading='{info['heading']}', actions='{info['first_actions']}', "
            f"weather='{info['default_weather']}', time='{info['default_time']}'"
        )
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


def _fallback_profiles(location_map: dict) -> dict:
    profiles = {"locations": {}}
    for loc in location_map:
        profiles["locations"][loc] = {
            "description": f"Unknown location: {loc}",
            "dimensions": "unknown",
            "materials": [],
            "lighting": "neutral",
            "ambience": "silent",
            "era": "present",
            "props": [],
            "special_features": []
        }
    return profiles


def _validate_and_fill(profiles: dict, location_map: dict) -> dict:
    profiles.setdefault("locations", {})
    default_profile = {
        "description": "Unknown.",
        "dimensions": "unknown",
        "materials": [],
        "lighting": "neutral",
        "ambience": "silent",
        "era": "present",
        "props": [],
        "special_features": []
    }
    for loc in location_map:
        if loc not in profiles["locations"]:
            profiles["locations"][loc] = default_profile.copy()
        else:
            for key, val in default_profile.items():
                if key not in profiles["locations"][loc]:
                    profiles["locations"][loc][key] = val
    return profiles
