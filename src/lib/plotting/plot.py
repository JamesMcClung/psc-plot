from abc import ABC, abstractmethod
from pathlib import Path

from lib.data.data_with_attrs import DataWithAttrs
from lib.data.keys import NAME_FRAGMENTS_KEY


class Plot[Data: DataWithAttrs](ABC):
    def __init__(self, data: Data):
        self.data = data

    @abstractmethod
    def show(self): ...

    @abstractmethod
    def _save_to_path(self, path: Path): ...

    @abstractmethod
    def _get_save_ext(self) -> str: ...

    def save(self, path_override: Path | None = None):
        path = path_override or "-".join(self.data.attrs[NAME_FRAGMENTS_KEY]) + self._get_save_ext()
        self._save_to_path(path)
        print(f"wrote to {path}")
