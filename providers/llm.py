"""
LLM Provider – abstract base + Ollama + OpenAI‑compatible implementations.
Includes validation to catch empty/short/dummy replies.
"""

from abc import ABC, abstractmethod
import requests
import json


class ProviderError(Exception):
    """Raised when a provider fails in a way that should trigger fallback."""
    pass


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str = "", temperature: float = 0.7,
                 max_tokens: int = 4096) -> str:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    def _validate_response(self, text: str, min_chars: int = 5):
        """
        Raise ProviderError if the response is empty, very short,
        or looks like a common refusal/dummy reply.
        """
        if not text or not text.strip():
            raise ProviderError("LLM returned empty response")
        if len(text.strip()) < min_chars:
            raise ProviderError(f"LLM returned very short response ({len(text)} chars): {text[:50]}")
        # Detect common refusal patterns
        lower = text.strip().lower()
        refusal_phrases = [
            "i don't know",
            "i cannot",
            "i'm not able",
            "as an ai",
            "i am unable",
        ]
        if any(lower.startswith(phrase) for phrase in refusal_phrases) and len(text) < 200:
            raise ProviderError(f"LLM returned likely refusal: {text[:100]}")
        return text


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt, system="", temperature=0.7, max_tokens=4096):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
            resp.raise_for_status()
            text = resp.json().get("response", "")
        except requests.RequestException as e:
            raise ProviderError(f"Ollama request failed: {e}")

        return self._validate_response(text)

    def health_check(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=10).ok
        except:
            return False


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, model: str, base_url: str, api_key: str = "not-needed"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def generate(self, prompt, system="", temperature=0.7, max_tokens=4096):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=120
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            raise ProviderError(f"OpenAI‑compatible request failed: {e}")

        return self._validate_response(text)

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=10)
            return resp.ok
        except:
            return False
