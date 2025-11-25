from abc import ABC, abstractmethod
from pathlib import Path


class Plot(ABC):
    @abstractmethod
    def show(self): ...

    @abstractmethod
    def save(self, path_override: Path | None = None): ...
