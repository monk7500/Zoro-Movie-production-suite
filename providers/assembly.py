"""
Assembly provider stubs.
"""

from abc import ABC, abstractmethod

class AssemblyProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    @property
    @abstractmethod
    def version(self) -> str: pass
    @abstractmethod
    def assemble(self, timeline: dict, output_path: str, credits_config: dict = None) -> str:
        pass
    @abstractmethod
    def health_check(self) -> bool: pass

class FFmpegAssemblyProvider(AssemblyProvider):
    name = "ffmpeg"
    version = "1.0"
    def assemble(self, timeline, output_path, credits_config=None):
        return output_path
    def health_check(self):
        return True
