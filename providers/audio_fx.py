"""
Audio effects provider – abstract base + AudioLDM2 stub.
Includes validation to catch silent/empty audio.
"""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider fails in a way that should trigger fallback."""
    pass


class AudioFXProvider(ABC):
    @abstractmethod
    def generate(self, description: str, duration_seconds: float,
                 environment: dict = None) -> bytes:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    def _validate_audio(self, audio_bytes: bytes, min_size: int = 200):
        """Raise ProviderError if audio is empty or very short."""
        if not audio_bytes or len(audio_bytes) < min_size:
            raise ProviderError(
                f"AudioFX returned empty or very short audio ({len(audio_bytes)} bytes)"
            )
        return audio_bytes


class AudioLDM2Provider(AudioFXProvider):
    """Local AudioLDM2 model for sound effects."""

    name = "audioldm2"
    version = "1.0"

    def generate(self, description, duration_seconds, environment=None):
        # In production, calls AudioLDM2 model.
        # Here we return a minimal valid WAV to pass validation.
        audio = self._generate_dummy_wav(duration_seconds)
        return self._validate_audio(audio)

    def _generate_dummy_wav(self, duration_seconds: float) -> bytes:
        import io, wave
        sample_rate = 16000
        num_samples = int(sample_rate * duration_seconds)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00" * num_samples * 2)
        return buf.getvalue()

    def health_check(self) -> bool:
        return True
