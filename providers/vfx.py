"""
VFX provider – abstract base + diffusion‑based implementation.
Includes blank‑frame detection to catch failed compositing.
"""

from abc import ABC, abstractmethod
import io, numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Optional


class ProviderError(Exception):
    """Raised when a provider fails in a way that should trigger fallback."""
    pass


class VFXProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def version(self) -> str: pass

    @abstractmethod
    def generate_effect(self, effect_description: dict,
                        background_frames: list,
                        shot_data: dict) -> List[str]:
        """Return list of composited frame paths."""
        pass

    @abstractmethod
    def health_check(self) -> bool: pass

    def _validate_frame(self, frame_path: str):
        """Raise ProviderError if the composited frame is blank."""
        try:
            img = Image.open(frame_path).convert("RGB")
            arr = np.array(img)
            if arr.std() < 5.0:
                raise ProviderError(
                    f"Blank VFX frame at {frame_path} (std={arr.std():.1f})"
                )
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Corrupt VFX frame at {frame_path}: {e}")


class DiffusionVFXProvider(VFXProvider):
    """Diffusion‑based VFX compositing (ComfyUI inpainting)."""

    name = "diffusion_vfx"
    version = "1.0"

    def generate_effect(self, effect_description, background_frames, shot_data) -> List[str]:
        # In production, calls ComfyUI or another inpainting model.
        # Here we create a dummy output frame sequence.
        output_dir = shot_data.get("output_dir", "vfx_temp")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        paths = []
        for i, bg in enumerate(background_frames if isinstance(background_frames, list) else [background_frames]):
            p = str(Path(output_dir) / f"vfx_frame_{i:04d}.png")
            # In production, composite the effect onto the background.
            # For the stub, we just copy the background (or generate a placeholder).
            try:
                if isinstance(bg, str) and Path(bg).exists():
                    img = Image.open(bg)
                else:
                    img = Image.new("RGB", (1920, 1080), color=(32, 32, 64))
                img.save(p)
                self._validate_frame(p)
                paths.append(p)
            except ProviderError:
                raise
            except Exception as e:
                raise ProviderError(f"Failed to generate VFX frame {i}: {e}")
        return paths

    def health_check(self) -> bool:
        return True
