"""
Continuity Watchdog – tracks fix attempts and escalates stuck errors.
"""

class ContinuityWatchdog:
    def __init__(self, max_attempts=3):
        self.attempts = {}
        self.max_attempts = max_attempts

    def can_fix(self, error_id: str) -> bool:
        return self.attempts.get(error_id, 0) < self.max_attempts

    def record_attempt(self, error_id: str):
        self.attempts[error_id] = self.attempts.get(error_id, 0) + 1

    def is_stuck(self, error_id: str) -> bool:
        return self.attempts.get(error_id, 0) >= self.max_attempts
