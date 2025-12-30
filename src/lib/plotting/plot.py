from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from lib.data.data_with_attrs import DataWithAttrs


class Plot[Data: DataWithAttrs](ABC):
    def __init__(self, data: Data):
        self.data = data
        self.hooks: list[Hook] = []

    def add_hook(self, hook: Hook):
        if not hook.is_compatible(self):
            raise Exception("TODO better error message")

        self.hooks.append(hook)

    @abstractmethod
    def show(self): ...

    @abstractmethod
    def _save_to_path(self, path: Path): ...

    @abstractmethod
    def _get_save_ext(self) -> str: ...

    def save(self, path_override: Path | None = None):
        path = path_override or "-".join(self.data.metadata.name_fragments) + self._get_save_ext()
        self._save_to_path(path)
        print(f"wrote to {path}")


class Hook:
    @abstractmethod
    def is_compatible(self, plot: Plot) -> bool: ...
