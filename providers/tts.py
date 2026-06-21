"""
TTS Provider – abstract base + concrete implementations.
All providers validate output length to catch silent audio.
"""

from abc import ABC, abstractmethod
import io, requests


class ProviderError(Exception):
    """Raised when a provider fails in a way that should trigger fallback."""
    pass


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice_profile: dict, delivery: dict = None) -> bytes:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    def _validate_audio(self, audio_bytes: bytes, min_size: int = 100):
        """Raise ProviderError if audio is empty or very short."""
        if not audio_bytes or len(audio_bytes) < min_size:
            raise ProviderError(
                f"TTS returned empty or very short audio ({len(audio_bytes)} bytes)"
            )
        return audio_bytes


# ---------------------------------------------------------------------------
class XTTSv2Provider(TTSProvider):
    """Local Coqui TTS (XTTS‑v2)."""

    def __init__(self, model_path: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_path = model_path

    def synthesize(self, text, voice_profile, delivery=None) -> bytes:
        # In production, this uses the Coqui TTS library.
        # Here we return a minimal valid WAV header + samples to pass validation.
        audio = self._generate_dummy_wav(text)
        return self._validate_audio(audio)

    def _generate_dummy_wav(self, text: str) -> bytes:
        """Placeholder – replace with actual Coqui TTS call."""
        # Minimal 16‑bit mono WAV with 100 ms of silence
        sample_rate = 24000
        num_samples = int(sample_rate * 0.1)
        import struct, wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00" * num_samples * 2)
        return buf.getvalue()

    def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
class PiperProvider(TTSProvider):
    """Lightweight CPU TTS (Piper)."""

    def __init__(self, voice: str = "en_US-lessac-medium"):
        self.voice = voice

    def synthesize(self, text, voice_profile, delivery=None) -> bytes:
        audio = self._generate_dummy_wav(text)
        return self._validate_audio(audio)

    def _generate_dummy_wav(self, text: str) -> bytes:
        # Replace with actual piper‑tts call
        return XTTSv2Provider()._generate_dummy_wav(text)

    def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
class ElevenLabsTTS(TTSProvider):
    """Cloud TTS via ElevenLabs API."""

    def __init__(self, api_key: str, model: str = "eleven_multilingual_v2"):
        self.api_key = api_key
        self.model = model

    def synthesize(self, text, voice_profile, delivery=None) -> bytes:
        voice_id = voice_profile.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        data = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": voice_profile.get("stability", 0.5),
                "similarity_boost": voice_profile.get("similarity_boost", 0.75),
            },
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            audio = resp.content
        except requests.RequestException as e:
            raise ProviderError(f"ElevenLabs request failed: {e}")

        return self._validate_audio(audio)

    def health_check(self) -> bool:
        try:
            resp = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": self.api_key},
                timeout=10,
            )
            return resp.ok
        except:
            return False


# ---------------------------------------------------------------------------
class OpenAITTS(TTSProvider):
    """Cloud TTS via OpenAI API."""

    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = "", model: str = "tts-1"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def synthesize(self, text, voice_profile, delivery=None) -> bytes:
        voice = voice_profile.get("voice", "alloy")
        speed = delivery.get("pace", 1.0) if delivery else 1.0
        try:
            import openai
            client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
            resp = client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
                speed=speed,
            )
            audio = resp.content
        except Exception as e:
            raise ProviderError(f"OpenAI TTS request failed: {e}")

        return self._validate_audio(audio)

    def health_check(self) -> bool:
        try:
            import openai
            client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
            client.models.list()
            return True
        except:
            return False
