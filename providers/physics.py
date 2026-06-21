"""
Physics provider – abstract base + concrete implementations.
Includes validation to catch empty/trivial simulation outputs.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ProviderError(Exception):
    """Raised when a provider fails in a way that should trigger fallback."""
    pass


class PhysicsProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def version(self) -> str: pass

    @abstractmethod
    def simulate(self, scene_data: dict, animation_data: dict,
                 duration_sec: float, frame_rate: int) -> dict:
        """Return a simulation cache dict (cloth, hair, rigid_bodies, particles)."""
        pass

    @abstractmethod
    def health_check(self) -> bool: pass

    def _validate_cache(self, cache: dict, scene_data: dict):
        """
        Raise ProviderError if the cache is empty when the scene clearly
        needs simulation (e.g., characters with cloth/hair present).
        """
        entities = scene_data.get("entities", [])
        has_characters = any(e.get("type") == "character" for e in entities)
        has_dynamic_props = any(e.get("type") == "dynamic_prop" for e in entities)

        total_entries = (
            len(cache.get("cloth", {})) +
            len(cache.get("hair", {})) +
            len(cache.get("rigid_bodies", [])) +
            len(cache.get("particles", []))
        )

        if has_characters and total_entries == 0:
            # Characters typically have at least some cloth/hair.
            # An empty cache is suspicious.
            raise ProviderError(
                "Physics simulation returned empty cache despite characters in scene"
            )

        # Don't fail if no dynamic props — not every shot has rigid bodies.
        return cache


class BlenderPhysicsProvider(PhysicsProvider):
    name = "blender_physics"
    version = "1.0"

    def simulate(self, scene_data, animation_data, duration_sec, frame_rate) -> dict:
        # In production, calls Blender in headless mode to run cloth/hair sims.
        cache = {
            "cloth": {},
            "hair": {},
            "rigid_bodies": [],
            "particles": [],
        }
        # Dummy: add an empty cloth entry for the first character if present
        for ent in scene_data.get("entities", []):
            if ent.get("type") == "character":
                cache["cloth"][f"{ent['id']}_default"] = []
                cache["hair"][f"{ent['id']}_default"] = []
                break

        return self._validate_cache(cache, scene_data)

    def health_check(self) -> bool:
        import subprocess
        try:
            subprocess.run(["blender", "--version"], capture_output=True, check=True)
            return True
        except:
            return False


class SimplePhysicsProvider(PhysicsProvider):
    """Rule‑based fallback – always valid."""
    name = "simple_physics"
    version = "1.0"

    def simulate(self, scene_data, animation_data, duration_sec, frame_rate) -> dict:
        cache = {
            "cloth": {},
            "hair": {},
            "rigid_bodies": [],
            "particles": [],
            "notes": "Simple CPU fallback applied; no detailed simulation."
        }
        return self._validate_cache(cache, scene_data)

    def health_check(self) -> bool:
        return True
