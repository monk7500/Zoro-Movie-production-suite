"""
Fault Propagation Decider – maps validator errors to root‑cause agents.
"""

class FaultPropagationDecider:
    def __init__(self, data_dep_index, graph):
        self.index = data_dep_index
        self.graph = graph

    def find_root_cause_agent(self, error: dict) -> str:
        mapping = {
            "WRONG_OUTFIT": "Character Visual Designer",
            "MISSING_INJURY": "Character Visual Designer",
            "PROP_MISSING": "Dynamic Prop Tracker",
            "PROP_WRONG_POSITION": "Dynamic Prop Tracker",
            "VEHICLE_WRONG_PLATE": "Population Generator",
            "GEOGRAPHY_MISMATCH": "Geography Definition Agent",
            "LIGHTING_WRONG_STATE": "Lighting Consistency Agent",
            "WEATHER_MISMATCH": "Environmental Effects Simulator",
            "JOINT_ANGLE_IMPOSSIBLE": "Animation Agent",
            "OBJECT_FLOATING": "Physics Simulator Agent",
            "FLICKER": "Render Agent",
            "COLOR_DRIFT": "Color Grading Agent",
            "LIPSYNC_OFF": "Lip‑Sync & Audio Alignment Agent",
        }
        return mapping.get(error.get("symptom", ""), "Render Agent")

    def generate_fix_instruction(self, error: dict) -> str:
        agent = self.find_root_cause_agent(error)
        shot_id = error.get("shot_id", "")
        if agent == "Render Agent":
            mask = error.get("mask_path")
            if mask:
                return f"RE‑RENDER_REGION: shot={shot_id}, frames={error.get('frame_range')}, mask={mask}"
            return f"RE‑RENDER_FULL: shot={shot_id}, frames={error.get('frame_range')}"
        return f"RE‑RUN_AGENT: agent={agent}, shot={shot_id}"
