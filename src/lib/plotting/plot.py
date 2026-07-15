from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from matplotlib import pyplot as plt

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.frame_data_traits import HasHookList
from lib.plotting.hook import Hook
from lib.plotting.renderer import Renderer

type SaveFormat = Literal["mp4", "gif", "png"]


class Plot[Data: DataWithAttrs](ABC):
    class AddHookData(HasHookList): ...

    def __init__(self, renderer: Renderer[Data], data: Data):
        self.renderer = renderer
        self.data = data
        self.hooks: list[Hook] = []
        self.fig, self.ax = plt.subplots(subplot_kw=renderer.subplot_kw())

    def add_hook(self, hook: Hook):
        self.hooks.append(hook)

        post_add_data = Plot.AddHookData(hooks=self.hooks)

        for hook in self.hooks.copy():  # hooks might reorder themselves
            hook.post_add_hook(post_add_data)

    @abstractmethod
    def show(self): ...

    @abstractmethod
    def save_to_path(self, path: Path, *, dpi: float | None = None): ...

    @abstractmethod
    def allowed_save_formats(self) -> list[SaveFormat]: ...

    def default_save_format(self) -> SaveFormat:
        return self.allowed_save_formats()[0]

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
