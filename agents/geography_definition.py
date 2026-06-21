"""
Agent 12: Geography Definition Agent
Produces a precise 3D spatial blueprint for every location:
room boundaries, fixed object positions, entrances, and coordinate system.
Processes ALL hard‑fixed props from the catalog — not just first‑scene props.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    location_profiles = input_slices.get("location_profiles", {}).get("locations", {})
    prop_catalog = input_slices.get("prop_catalog", {}).get("props", {})

    if not location_profiles:
        empty = {"locations": {}}
        output_json = json.dumps(empty, indent=2, ensure_ascii=False)
        content_hash = hashlib.sha256(output_json.encode()).hexdigest()
        empty["_meta"] = {
            "agent": "GeographyDefinitionAgent",
            "bible_version": bible_version,
            "content_hash": content_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        final_json = json.dumps(empty, indent=2, ensure_ascii=False)
        return {"geography.json": final_json.encode("utf-8")}

    # 1. Group ALL props by their typical location
    props_by_location = _group_props_by_location(prop_catalog, location_profiles)

    # 2. Build enriched location summaries with all props
    location_summaries = _build_location_summaries(location_profiles, props_by_location)

    # 3. LLM‑based spatial planning
    system_prompt = _build_system_prompt()
    user_prompt = f"Location summaries:\n{location_summaries}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=16384
        )
        geo_data = _extract_json(response)
    except Exception:
        geo_data = _fallback_geography(location_profiles, props_by_location)

    # 4. Validate and fill (ensures every hard‑fixed prop is placed)
    geo_data = _validate_and_fill(geo_data, location_profiles, props_by_location)

    # 5. Compute content hash WITHOUT _meta
    clean_data = {k: v for k, v in geo_data.items() if k != "_meta"}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    # 6. Add metadata
    geo_data["_meta"] = {
        "agent": "GeographyDefinitionAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(geo_data, indent=2, ensure_ascii=False)
    return {"geography.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a set designer and spatial planner. For each location, produce a spatial blueprint as JSON.

For each location, provide:
- "boundary": { "type": "rectangle" (or "irregular" with "points" array), "width_m": number, "depth_m": number, "height_m": number }
- "fixed_objects": array of all hard‑fixed objects. Each object has:
    - "id": prop name
    - "type": "furniture", "lighting", "structural", "fixture"
    - "position": { "x": float, "y": float, "z": float } — meters, relative to center of floor
    - "dimensions": { "width": float, "depth": float, "height": float }
    - "rotation_y": degrees around vertical axis
- "entrances": array of doorways/openings:
    - "id": descriptive name
    - "position": { "x": float, "y": float, "z": float }
    - "width": float (meters)
    - "type": "door", "archway", "window", "hatch"

RULES:
- Origin (0,0,0) = center of floor. +X right, +Y forward, +Z up.
- Place ALL listed hard‑fixed objects. Do not skip any.
- No overlapping objects.
- Entrances on boundary edges.
- Typical sizes: bar counter 6x1x1.2m, table 1.5x1x0.75m, chair 0.4x0.4x0.8m, door width 1.0-1.2m, neon sign 1.5x0.1x0.5m at z≈2.0-2.5m.
- Output ONLY valid JSON. Top key: "locations"."""


def _group_props_by_location(prop_catalog: dict, location_profiles: dict) -> dict:
    """Group every prop from the catalog into its typical location."""
    props_by_loc = {loc: {"hard_fixed": [], "dynamic": []} for loc in location_profiles}
    for prop_name, prop_data in prop_catalog.items():
        loc = prop_data.get("location_typical", "")
        if loc not in props_by_loc:
            loc = _infer_location(prop_name, prop_data, location_profiles)
            if not loc:
                continue
            if loc not in props_by_loc:
                props_by_loc[loc] = {"hard_fixed": [], "dynamic": []}
        classification = prop_data.get("classification", "dynamic")
        entry = {
            "name": prop_name,
            "type": prop_data.get("type", "prop"),
            "subtype": prop_data.get("subtype", ""),
            "material": prop_data.get("material", ""),
            "color": prop_data.get("color", ""),
            "dimensions": prop_data.get("dimensions", "unknown"),
            "default_state": prop_data.get("default_state", "")
        }
        if classification == "hard_fixed":
            props_by_loc[loc]["hard_fixed"].append(entry)
        else:
            props_by_loc[loc]["dynamic"].append(entry)
    return props_by_loc


def _infer_location(prop_name: str, prop_data: dict, location_profiles: dict) -> str:
    context = prop_data.get("context", "").lower()
    for loc in location_profiles:
        if loc.lower() in context:
            return loc
    return ""


def _build_location_summaries(location_profiles: dict, props_by_location: dict) -> str:
    parts = []
    for loc_name, profile in location_profiles.items():
        dims = profile.get("dimensions", "unknown")
        hard = props_by_location.get(loc_name, {}).get("hard_fixed", [])
        dynamic = props_by_location.get(loc_name, {}).get("dynamic", [])
        hard_names = [p["name"] for p in hard]
        dynamic_names = [p["name"] for p in dynamic]
        specials = profile.get("special_features", [])
        parts.append(
            f"{loc_name}:\n  Dimensions: {dims}\n  Description: {profile.get('description', '')}\n"
            f"  Hard‑fixed props: {hard_names}\n  Dynamic props: {dynamic_names}\n  Special: {specials}"
        )
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


def _fallback_geography(location_profiles: dict, props_by_location: dict) -> dict:
    geo = {"locations": {}}
    for loc_name in location_profiles:
        boundary = {"type": "rectangle", "width_m": 5.0, "depth_m": 5.0, "height_m": 2.5}
        fixed_objects = []
        hard_props = props_by_location.get(loc_name, {}).get("hard_fixed", [])
        for i, prop in enumerate(hard_props):
            row, col = i // 4, i % 4
            fixed_objects.append({
                "id": prop["name"],
                "type": prop.get("subtype", "furniture"),
                "position": {"x": -2.0 + col * 1.5, "y": -2.0 + row * 1.5, "z": 0.0},
                "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                "rotation_y": 0.0
            })
        geo["locations"][loc_name] = {
            "boundary": boundary,
            "fixed_objects": fixed_objects,
            "entrances": [{"id": "main_door", "position": {"x": 0.0, "y": 2.5, "z": 0.0}, "width": 1.0, "type": "door"}]
        }
    return geo


def _validate_and_fill(geo_data: dict, location_profiles: dict, props_by_location: dict) -> dict:
    geo_data.setdefault("locations", {})
    for loc_name in location_profiles:
        if loc_name not in geo_data["locations"]:
            geo_data["locations"][loc_name] = _create_default_geography(loc_name, props_by_location)
        else:
            loc_geo = geo_data["locations"][loc_name]
            loc_geo.setdefault("boundary", {"type": "rectangle", "width_m": 5.0, "depth_m": 5.0, "height_m": 2.5})
            loc_geo.setdefault("fixed_objects", [])
            loc_geo.setdefault("entrances", [{"id": "main_door", "position": {"x": 0.0, "y": 2.5, "z": 0.0}, "width": 1.0, "type": "door"}])
            expected_hard = {p["name"] for p in props_by_location.get(loc_name, {}).get("hard_fixed", [])}
            placed_hard = {obj["id"] for obj in loc_geo["fixed_objects"]}
            for missing_name in expected_hard - placed_hard:
                loc_geo["fixed_objects"].append({
                    "id": missing_name,
                    "type": "furniture",
                    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
                    "rotation_y": 0.0
                })
    return geo_data


def _create_default_geography(loc_name: str, props_by_location: dict) -> dict:
    hard = props_by_location.get(loc_name, {}).get("hard_fixed", [])
    fixed_objects = []
    for i, prop in enumerate(hard):
        row, col = i // 4, i % 4
        fixed_objects.append({
            "id": prop["name"],
            "type": prop.get("subtype", "furniture"),
            "position": {"x": -2.0 + col * 1.5, "y": -2.0 + row * 1.5, "z": 0.0},
            "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
            "rotation_y": 0.0
        })
    return {
        "boundary": {"type": "rectangle", "width_m": 5.0, "depth_m": 5.0, "height_m": 2.5},
        "fixed_objects": fixed_objects,
        "entrances": [{"id": "main_door", "position": {"x": 0.0, "y": 2.5, "z": 0.0}, "width": 1.0, "type": "door"}]
        }
