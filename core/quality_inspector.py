"""
Quality Inspector – aggregates validator reports into a fix plan.
"""

class QualityInspector:
    def __init__(self, decider):
        self.decider = decider

    def inspect(self, errors: list) -> dict:
        fix_plan = []
        for err in errors:
            root = self.decider.find_root_cause_agent(err)
            fix_plan.append({"error_id": err.get("error_id"), "root_agent": root})
        return {"fix_plan": fix_plan, "total_fixes": len(fix_plan)}
