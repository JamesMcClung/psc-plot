from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.frame_data_traits import HasHookList
from lib.plotting.hook import Hook

type SaveFormat = Literal["mp4", "gif", "png"]


class Plot[Data: DataWithAttrs](ABC):
    class AddHookData(HasHookList): ...

    def __init__(self, data: Data):
        self.data = data
        self.hooks: list[Hook] = []

    def add_hook(self, hook: Hook):
        self.hooks.append(hook)

        post_add_data = Plot.AddHookData(hooks=self.hooks)

        for hook in self.hooks.copy():  # hooks might reorder themselves
            hook.post_add_hook(post_add_data)

    @abstractmethod
    def show(self): ...

    @abstractmethod
    def _save_to_path(self, path: Path): ...

    @abstractmethod
    def allowed_save_formats(self) -> list[SaveFormat]: ...

    def default_save_format(self) -> SaveFormat:
        return self.allowed_save_formats()[0]

    def save(self, dir: Path, format: SaveFormat | None = None):
        format = format or self.default_save_format()
        name = "-".join(self.data.metadata.name_fragments) + "." + format
        path = dir / name
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
