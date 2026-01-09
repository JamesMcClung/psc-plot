from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.hook import Hook


class Plot[Data: DataWithAttrs](ABC):
    def __init__(self, data: Data):
        self.data = data
        self.hooks: list[Hook] = []

    def add_hook(self, hook: Hook):
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

    def pre_init_fig(self, init_data: Any):
        for hook in self.hooks:
            hook.pre_init_fig(init_data)

    def post_init_fig(self, init_data: Any):
        for hook in self.hooks:
            hook.post_init_fig(init_data)

    def pre_update_fig(self, update_data: Any):
        for hook in self.hooks:
            hook.pre_update_fig(update_data)

    def post_update_fig(self, update_data: Any):
        for hook in self.hooks:
            hook.post_update_fig(update_data)
