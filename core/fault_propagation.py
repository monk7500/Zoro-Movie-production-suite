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
            "PROP_MISSING": "Dynamic Prop Tracker",
            "FLICKER": "Render Agent",
            "COLOR_DRIFT": "Color Grading Agent",
            "LIPSYNC_OFF": "Lip‑Sync & Audio Alignment Agent"
        }
        return mapping.get(error.get("symptom", ""), "Render Agent")
