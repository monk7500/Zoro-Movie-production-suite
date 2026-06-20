"""
Audio effects provider stubs.
"""

from abc import ABC, abstractmethod

class AudioFXProvider(ABC):
    @abstractmethod
    def generate(self, description: str, duration_seconds: float, environment: dict = None) -> bytes:
        pass
    @abstractmethod
    def health_check(self) -> bool:
        pass

class AudioLDM2Provider(AudioFXProvider):
    def generate(self, description, duration_seconds, environment=None):
        return b""
    def health_check(self):
        return True
