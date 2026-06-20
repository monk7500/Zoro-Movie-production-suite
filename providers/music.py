"""
Music provider stubs.
"""

from abc import ABC, abstractmethod

class MusicProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, duration_seconds: float, key: str = "C minor", tempo_bpm: int = 90, instruments: list = None) -> bytes:
        pass
    @abstractmethod
    def health_check(self) -> bool:
        pass

class MusicGenProvider(MusicProvider):
    def generate(self, prompt, duration_seconds, key="C minor", tempo_bpm=90, instruments=None):
        return b""
    def health_check(self):
        return True
