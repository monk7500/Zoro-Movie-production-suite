"""
Image generation provider base class and ComfyUI stub.
"""

from abc import ABC, abstractmethod

class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, negative: str = "", width: int = 1024, height: int = 1024, seed: int = 42) -> bytes:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

class ComfyUIProvider(ImageProvider):
    def __init__(self, base_url: str = "http://localhost:8188"):
        self.base_url = base_url

    def generate(self, prompt, negative="", width=1024, height=1024, seed=42):
        # Will call ComfyUI API
        return b""

    def health_check(self):
        import requests
        try:
            return requests.get(f"{self.base_url}/").ok
        except:
            return False
