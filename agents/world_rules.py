"""
Agent 10: World Rules Agent
Extracts explicit and implied rules of the story universe from the screenplay
and any creator‑provided world guide. Outputs a structured rulebook that constrains
physics, magic, technology, species, and social systems.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    world_guide = input_slices.get("world_guide") or ""

    scenes = parsed_script.get("scenes", [])

    # 1. Extract rule‑like snippets from the script
    rule_snippets = _extract_rule_snippets(scenes)

    # 2. LLM‑based rule extraction
    system_prompt = _build_system_prompt()
    user_prompt = f"Script rule‑like excerpts:\n{rule_snippets}\n\nWorld guide (creator notes):\n{world_guide}"

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
            max_tokens=12288
        )
        rules = _extract_json(response)
    except Exception:
        rules = _fallback_rules()

    # 3. Validate and fill
    rules = _validate_and_fill(rules)

    # 4. Add metadata
    output_json = json.dumps(rules, indent=2, ensure_ascii=False)
    rules["_meta"] = {
        "agent": "WorldRulesAgent",
        "bible_version": bible_version,
        "content_hash": hashlib.sha256(output_json.encode()).hexdigest(),
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"world_rules.json": output_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    return """You are a world‑building analyst. Extract all explicit and implied rules of the story universe from the provided script and world guide.

Organize the rules into a JSON object with domain‑specific sections. Choose domain names that match the story content. Common domains:
- "physical_laws": { "gravity": "earth_normal"|"zero"|"variable", "time_flow": "linear"|"nonlinear"|"looping" }
- "magic_system": { "exists": true|false, "rules": ["..."], "cost": "...", "limitations": ["..."] }
- "technology_level": e.g., "present_day", "near_future_2087", "medieval", "space_faring"
- "species": { "SPECIES_NAME": { "anatomy": "...", "abilities": ["..."], "limitations": ["..."] } }
- "social_norms": { "currency": "...", "law_enforcement": "...", "taboos": ["..."] }
- "transportation": { "flying_cars": true|false, "ground_vehicles": ["..."], "space_travel": "none"|"interplanetary" }
- "communication": { "method": "...", "range": "planetary"|"local" }
- "health_medicine": { "level": "modern"|"advanced"|"magical"|"primitive", "notes": "..." }

There is NO fixed list of domains — create whatever is relevant. If not addressed, omit or mark "unknown".
Do NOT invent rules that contradict the script. Output ONLY valid JSON."""


def _extract_rule_snippets(scenes: List[dict]) -> str:
    keywords = [
        "can't", "cannot", "must", "mustn't", "always", "never", "only",
        "rule", "law", "physics", "magic", "technology", "gravity",
        "impossible", "forbidden", "every", "nobody", "everyone",
        "since the", "after the war", "before the", "when the",
        "years ago", "centuries", "decades"
    ]
    snippets = []
    for scene in scenes:
        for line in scene.get("action_lines", []):
            if any(kw in line.lower() for kw in keywords):
                snippets.append(f"[{scene['id']}] {line}")
        for d in scene.get("dialogue", []):
            line = d.get("line", "")
            if any(kw in line.lower() for kw in keywords):
                snippets.append(f"[{scene['id']}] {d.get('character', '')}: {line}")
    if not snippets:
        for scene in scenes[:3]:
            for line in scene.get("action_lines", [])[:3]:
                snippets.append(f"[{scene['id']}] {line}")
    return "\n".join(snippets[:50])


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


def _fallback_rules() -> dict:
    return {
        "physical_laws": {"gravity": "earth_normal", "time_flow": "linear"},
        "magic_system": {"exists": False},
        "technology_level": "present_day",
        "species": {},
        "social_norms": {},
        "transportation": {},
        "communication": {}
    }


def _validate_and_fill(rules: dict) -> dict:
    defaults = {
        "physical_laws": {"gravity": "earth_normal", "time_flow": "linear"},
        "magic_system": {"exists": False, "rules": [], "cost": "", "limitations": []},
        "technology_level": "present_day",
        "species": {},
        "social_norms": {},
        "transportation": {},
        "communication": {}
    }
    for domain, default in defaults.items():
        if domain not in rules:
            rules[domain] = default
    return rules
