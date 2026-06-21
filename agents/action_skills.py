"""
Agent 24: Action Skills Agent
Converts action lines into structured action choreography per character, per scene.
Defines action type, timing, intensity, style, target props/characters, and movement paths.
Drives the Animation Agent.
"""

import json, re, hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def run(input_slices: Dict[str, Any], bible_version: str, llm_provider) -> Dict[str, bytes]:
    parsed_script = input_slices.get("parsed_script", {})
    personas = input_slices.get("character_personas", {}).get("characters", {})
    wardrobe = input_slices.get("wardrobe_timeline", {}).get("characters", {})
    world_rules = input_slices.get("world_rules", {})
    geography = input_slices.get("geography", {}).get("locations", {})
    prop_states = input_slices.get("prop_classification", {}).get("props", {})

    scenes = parsed_script.get("scenes", [])
    output_choreography = {"scenes": {}}

    for scene in scenes:
        sid = scene["id"]
        actions = scene.get("action_lines", [])
        chars_in_scene = scene.get("characters_in_scene", [])
        if not actions or not chars_in_scene:
            continue

        # Build character context for the scene
        char_context = _build_character_context(chars_in_scene, personas, wardrobe, sid)

        location = scene.get("location", "")
        geo = geography.get(location, {})
        # Gather props available in this location
        available_props = _get_available_props(location, prop_states)

        # LLM‑based action extraction
        choreography = _extract_choreography(
            scene_id=sid,
            actions=actions,
            characters=char_context,
            geography=geo,
            available_props=available_props,
            world_rules=world_rules,
            llm_provider=llm_provider
        )

        output_choreography["scenes"][sid] = {"characters": choreography}

    # ---- Metadata fix ----
    clean_data = {"scenes": output_choreography["scenes"]}
    output_json = json.dumps(clean_data, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(output_json.encode()).hexdigest()

    output_choreography["_meta"] = {
        "agent": "ActionSkillsAgent",
        "bible_version": bible_version,
        "content_hash": content_hash,
        "timestamp": datetime.utcnow().isoformat()
    }

    final_json = json.dumps(output_choreography, indent=2, ensure_ascii=False)
    return {"action_choreography.json": final_json.encode("utf-8")}


# ---------------------------------------------------------------------------
def _build_character_context(chars: List[str], personas: dict, wardrobe: dict, scene_id: str) -> dict:
    ctx = {}
    for name in chars:
        persona = personas.get(name, {})
        physical = _get_physical_for_scene(name, scene_id, wardrobe)
        ctx[name] = {
            "personality_traits": persona.get("personality_traits", {}),
            "archetype": persona.get("archetype", "everyman"),
            "physical_state": physical,
            "emotional_state": persona.get("emotional_range", ["neutral"])[0]
        }
    return ctx


def _get_physical_for_scene(char_name: str, scene_id: str, wardrobe: dict) -> dict:
    timeline = wardrobe.get(char_name, {}).get("timeline", [])
    for entry in timeline:
        if entry.get("scene") == scene_id:
            return entry.get("physical", {})
    return {}


def _get_available_props(location: str, prop_states: dict) -> List[str]:
    """Return list of prop names that are in the given location."""
    props = []
    for pname, pdata in prop_states.items():
        if pdata.get("location") == location:
            props.append(pname)
    return props


def _extract_choreography(scene_id: str, actions: List[str], characters: dict,
                          geography: dict, available_props: List[str],
                          world_rules: dict, llm_provider) -> dict:
    system_prompt = """You are a fight choreographer and movement director. Convert the provided action lines into a precise, machine-readable action sequence for each character.

Output a JSON object where each key is a character name, and its value is an object with an "actions" array. Each action has:
- "action_id": unique ID (e.g., S01_JANE_001)
- "type": verb describing the action: "walk", "run", "sit", "stand", "drink", "fight", "shoot", "forge", "climb", "dance", "fall", "crawl", "dodge", "throw", "pick_up", "drop", "open", "close", "push", "pull", "swim", "fly", "teleport" – use whatever matches the script.
- "start_time_seconds": estimated start time from scene beginning (can be 0.0)
- "duration_seconds": estimated duration
- "target_prop": prop name if action involves a specific object (omit if none)
- "target_character": character name if action involves another character (fight, talk to, etc.)
- "path": array of {x, y, z} positions if movement covers ground (walk, run). Can be empty if no path.
- "intensity": 0.0 (calm) to 1.0 (extreme)
- "style": descriptive style of the movement (e.g., "limping, desperate", "graceful, predatory")
- "notes": any additional detail from the action line

Consider the character's physical state (injuries, dirt, wetness), persona, and available props. If an action is implied but not explicit, infer it logically (e.g., a character sitting at a bar must have walked there unless already seated).
Output ONLY valid JSON. No commentary."""

    user_prompt = (
        f"Scene ID: {scene_id}\n"
        f"Characters context:\n{json.dumps(characters, indent=2)}\n\n"
        f"Action lines:\n" + "\n".join(actions) + "\n\n"
        f"Available props: {available_props}\n"
        f"Geography: {json.dumps(geography)}"
    )

    try:
        response = llm_provider.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=8192
        )
        choreo = _extract_json(response)
        if not isinstance(choreo, dict):
            return {}
        return choreo
    except Exception:
        # Fall back to simple idle actions
        fallback = {}
        for name in characters:
            fallback[name] = {
                "actions": [
                    {
                        "action_id": f"{scene_id}_{name}_001",
                        "type": "idle",
                        "start_time_seconds": 0.0,
                        "duration_seconds": 5.0,
                        "intensity": 0.1,
                        "style": "neutral idle",
                        "notes": "Auto‑generated fallback."
                    }
                ]
            }
        return fallback


def _extract_json(response: str) -> Any:
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
