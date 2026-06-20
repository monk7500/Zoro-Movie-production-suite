"""
Render engine provider stubs.
"""

from abc import ABC, abstractmethod

class RenderEngineProvider(ABC):
    @abstractmethod
    def render_shot(self, shot_data: dict, output_dir: str, frame_range: tuple = None, mask: dict = None, original_frame_dir: str = None) -> list:
        pass
    @abstractmethod
    def apply_lighting_rig(self, shot_id: str, lighting_plan: dict, geography: dict, entities: list, style_defaults: dict = None, environment: dict = None) -> dict:
        pass
    @abstractmethod
    def health_check(self) -> bool:
        pass

class ComfyUIRenderProvider(RenderEngineProvider):
    def render_shot(self, shot_data, output_dir, frame_range=None, mask=None, original_frame_dir=None):
        return []
    def apply_lighting_rig(self, shot_id, lighting_plan, geography, entities, style_defaults=None, environment=None):
        return {}
    def health_check(self):
        return True
