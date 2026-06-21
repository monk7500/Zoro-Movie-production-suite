"""
Render engine provider – abstract base + concrete implementations.
All providers validate output frames to catch blank renders.
"""

from abc import ABC, abstractmethod
import io, numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Optional


class ProviderError(Exception):
    """Raised when a provider fails in a way that should trigger fallback."""
    pass


class RenderEngineProvider(ABC):
    @abstractmethod
    def render_shot(self, shot_data: dict, output_dir: str,
                    frame_range: Optional[tuple] = None,
                    mask: Optional[dict] = None,
                    original_frame_dir: Optional[str] = None) -> List[str]:
        """Render frames for a shot. Returns list of frame file paths."""
        pass

    @abstractmethod
    def apply_lighting_rig(self, shot_id: str, lighting_plan: dict,
                           geography: dict, entities: list,
                           style_defaults: dict = None,
                           environment: dict = None) -> dict:
        """Returns a light rig manifest."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    def _validate_frame(self, frame_path: str):
        """Raise ProviderError if the rendered frame is blank (solid color)."""
        try:
            img = Image.open(frame_path).convert("RGB")
            arr = np.array(img)
            if arr.std() < 5.0:
                raise ProviderError(
                    f"Blank frame detected at {frame_path} (std={arr.std():.1f})"
                )
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Corrupt frame at {frame_path}: {e}")


# ---------------------------------------------------------------------------
class ComfyUIRenderProvider(RenderEngineProvider):
    """AI‑based rendering via ComfyUI (SDXL / Flux)."""

    name = "comfyui"
    version = "1.0"

    def render_shot(self, shot_data, output_dir, frame_range=None, mask=None,
                    original_frame_dir=None) -> List[str]:
        # In production, calls ComfyUI API to generate frames.
        # Here we create a dummy PNG sequence.
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        duration = shot_data.get("animation", {}).get("duration_seconds", 5.0)
        frame_count = max(1, int(duration * 24))
        paths = []
        for i in range(frame_count):
            p = out / f"frame_{i:04d}.png"
            self._write_dummy_frame(p)
            self._validate_frame(str(p))
            paths.append(str(p))
        return paths

    def apply_lighting_rig(self, shot_id, lighting_plan, geography, entities,
                           style_defaults=None, environment=None) -> dict:
        return {"key_light": {"position": {"x": 2, "y": -3, "z": 2.5}, "intensity": 1.0}}

    def _write_dummy_frame(self, path: Path):
        img = Image.new("RGB", (1920, 1080), color=(32, 32, 32))
        img.save(path)

    def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
class BlenderRenderProvider(RenderEngineProvider):
    """3D rendering via Blender (Cycles / Eevee)."""

    name = "blender"
    version = "1.0"

    def render_shot(self, shot_data, output_dir, frame_range=None, mask=None,
                    original_frame_dir=None) -> List[str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        # In production, calls Blender in headless mode.
        paths = []
        for i in range(24):  # dummy frame count
            p = out / f"frame_{i:04d}.png"
            self._write_dummy_frame(p)
            self._validate_frame(str(p))
            paths.append(str(p))
        return paths

    def apply_lighting_rig(self, shot_id, lighting_plan, geography, entities,
                           style_defaults=None, environment=None) -> dict:
        return {}

    def _write_dummy_frame(self, path: Path):
        img = Image.new("RGB", (1920, 1080), color=(16, 16, 16))
        img.save(path)

    def health_check(self) -> bool:
        import subprocess
        try:
            subprocess.run(["blender", "--version"], capture_output=True, check=True)
            return True
        except:
            return False


# ---------------------------------------------------------------------------
class UnrealRenderProvider(RenderEngineProvider):
    """Real‑time rendering via Unreal Engine."""

    name = "unreal"
    version = "1.0"

    def render_shot(self, shot_data, output_dir, frame_range=None, mask=None,
                    original_frame_dir=None) -> List[str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for i in range(24):
            p = out / f"frame_{i:04d}.png"
            self._write_dummy_frame(p)
            self._validate_frame(str(p))
            paths.append(str(p))
        return paths

    def apply_lighting_rig(self, shot_id, lighting_plan, geography, entities,
                           style_defaults=None, environment=None) -> dict:
        return {}

    def _write_dummy_frame(self, path: Path):
        img = Image.new("RGB", (1920, 1080), color=(8, 8, 8))
        img.save(path)

    def health_check(self) -> bool:
        return False  # Unreal not expected to run headless by default
