"""
Physics provider stubs.
"""

from abc import ABC, abstractmethod

class PhysicsProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    @property
    @abstractmethod
    def version(self) -> str: pass
    @abstractmethod
    def simulate(self, scene_data: dict, animation_data: dict, duration_sec: float, frame_rate: int) -> dict:
        pass
    @abstractmethod
    def health_check(self) -> bool: pass

class BlenderPhysicsProvider(PhysicsProvider):
    name = "blender_physics"
    version = "1.0"
    def simulate(self, scene_data, animation_data, duration_sec, frame_rate):
        return {}
    def health_check(self):
        return True
