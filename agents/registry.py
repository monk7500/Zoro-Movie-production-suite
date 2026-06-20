"""
Agent registry – maps agent names to their input contracts and run functions.
In the full project, this file imports all 48 agents.
"""

REGISTRY = {
    "Script Parser": {
        "input_spec": {
            "script_raw": "meta.script_raw",
            "mode": "meta.mode"
        },
        "model_version": "1.0",
        "required_providers": [],
        "max_retries": 2,
        "retry_delay": 1.0,
        "run_func": None  # will be set when agent modules are loaded
    },
    # ... other agents
}
