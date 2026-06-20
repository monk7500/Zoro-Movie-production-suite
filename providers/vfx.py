"""
VFX provider stubs.
"""

from abc import ABC, abstractmethod

class VFXProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    @property
    @abstractmethod
    def version(self) -> str: pass
    @abstractmethod
    def generate_effect(self, effect_description: dict, background_frames, shot_data: dict):
        pass
    @abstractmethod
    def health_check(self) -> bool: pass

class DiffusionVFXProvider(VFXProvider):
    name = "diffusion_vfx"
    version = "1.0"
    def generate_effect(self, effect_description, background_frames, shot_data):
        return background_frames
    def health_check(self):
        return True
