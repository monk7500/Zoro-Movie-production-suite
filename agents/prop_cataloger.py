"""
Agent 11: Prop & Set Dressing Cataloger
Enriches all discovered entities and props with production‑ready details:
material, color, dimensions, default state, classification, and typical location.
Outputs the definitive prop catalog that feeds Geography Definition, Prop Classifier,
and Prop Continuity Validator.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    entities = input_slices.get("entities", [])
    props = input_slices.get("props", [])
    locations = input_slices.get("location_profiles", {}).get("locations", {})
    world_rules = input_slices.get("world_rules", {})

    # 1. Merge entities and props into a unified item list
    all_items = _merge_items(entities, props)

    if not all_items:
        empty = {"props": {}}
        return {"prop_catalog.json": json.dumps(empty, indent=2).encode("utf-8")}

    # 2. Build a summary for the LLM
    item_summaries = _build_item_summaries(all_items)

    # 3. LLM‑based catalog generation
    system_prompt = _build_system_prompt()
    user_prompt = f"Items:\n{item_summaries}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=16384
        )
        catalog = _extract_json(response)
    except Exception:
        catalog = _fallback_catalog(all_items)

    # 4. Validate and fill missing items
    catalog = _validate_and_fill(catalog, all_items, locations)

    # 5. Add metadata
    output_json = json.dumps(catalog, indent=2, ensure_ascii=False)
    catalog["_meta"] = {
        "agent": "PropSetDressingCataloger",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"prop_catalog.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a props master. For each item listed, produce a detailed prop catalog entry as JSON.

For each prop, include these EXACT keys:
- "type": entity type (prop, vehicle, weapon, clothing, furniture, animal, machine, etc.)
- "subtype": more specific category (e.g., "container", "lighting", "seating", "firearm")
- "material": primary material(s) (e.g., "ceramic", "rusted_metal", "ebony_wood")
- "color": dominant color or palette
- "dimensions": approximate size (e.g., "standard mug, approx 10cm tall", "2m x 1.5m x 1m")
- "default_state": state when first encountered (e.g., "clean, empty", "flickering")
- "classification": "dynamic" if movable, "hard_fixed" if part of the set
- "location_typical": location(s) where it typically appears
- "visual_reference": placeholder path "props/NAME_ref.png"

Base details on provided context and attributes. If unknown, use reasonable defaults but note "assumed" in "_notes".
Output ONLY valid JSON. Top key must be "props"."""


def _merge_items(entities: List[dict], props: List[dict]) -> List[dict]:
    all_items = []
    seen = set()
    for ent in entities:
        name = ent.get("name", "").lower().replace(" ", "_")
        if name and name not in seen:
            seen.add(name)
            all_items.append({
                "name": name,
                "type": ent.get("type", "prop"),
                "subtype": ent.get("subtype", ""),
                "context": ent.get("context", ""),
                "first_mentioned": ent.get("first_mentioned", ""),
                "attributes": ent.get("attributes", {})
            })
    for prop in props:
        name = prop.get("name", "").lower().replace(" ", "_")
        if name and name not in seen:
            seen.add(name)
            all_items.append({
                "name": name,
                "type": "prop",
                "subtype": "",
                "context": prop.get("context", ""),
                "first_mentioned": prop.get("first_mentioned", ""),
                "attributes": {}
            })
    return all_items


def _build_item_summaries(all_items: List[dict]) -> str:
    parts = []
    for item in all_items:
        parts.append(
            f"{item['name']}: type={item['type']}, subtype={item['subtype']}, "
            f"context='{item['context']}', first_scene={item['first_mentioned']}, "
            f"attrs={item['attributes']}"
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


def _fallback_catalog(all_items: List[dict]) -> dict:
    catalog = {"props": {}}
    for item in all_items:
        name = item["name"]
        catalog["props"][name] = {
            "type": item.get("type", "prop"),
            "subtype": item.get("subtype", ""),
            "material": "unknown",
            "color": "unknown",
            "dimensions": "unknown",
            "default_state": "unknown",
            "classification": "dynamic",
            "location_typical": item.get("first_mentioned", ""),
            "visual_reference": f"props/{name}_ref.png",
            "_notes": "Auto‑generated fallback."
        }
    return catalog


def _validate_and_fill(catalog: dict, all_items: List[dict], locations: dict) -> dict:
    catalog.setdefault("props", {})
    default_entry = {
        "type": "prop", "subtype": "",
        "material": "unknown", "color": "unknown",
        "dimensions": "unknown", "default_state": "unknown",
        "classification": "dynamic", "location_typical": "",
        "visual_reference": ""
    }
    for item in all_items:
        name = item["name"]
        if name not in catalog["props"]:
            catalog["props"][name] = default_entry.copy()
            catalog["props"][name]["visual_reference"] = f"props/{name}_ref.png"
        else:
            for key, val in default_entry.items():
                if key not in catalog["props"][name]:
                    catalog["props"][name][key] = val
            if not catalog["props"][name].get("visual_reference"):
                catalog["props"][name]["visual_reference"] = f"props/{name}_ref.png"
        if not catalog["props"][name].get("location_typical"):
            # Try to infer from context or first mentioned scene
            scene_id = item.get("first_mentioned", "")
            catalog["props"][name]["location_typical"] = "unknown"
    return catalog
