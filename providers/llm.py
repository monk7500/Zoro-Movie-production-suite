import requests, json
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        pass
    @abstractmethod
    def health_check(self) -> bool:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt, system="", temperature=0.7, max_tokens=4096):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        resp = requests.post(f"{self.base_url}/api/generate", json=payload)
        return resp.json()["response"]

    def health_check(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/tags").ok
        except:
            return False

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, model: str, base_url: str, api_key: str = "not-needed"):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key

    def generate(self, prompt, system="", temperature=0.7, max_tokens=4096):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
        return resp.json()["choices"][0]["message"]["content"]

    def health_check(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/models").ok
        except:
            return False
