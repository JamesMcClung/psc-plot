from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from matplotlib import pyplot as plt

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.frame_data_traits import HasHookList
from lib.plotting.hook import Hook
from lib.plotting.renderer import Renderer
from lib.plotting.setup_fig import setup_fig

type SaveFormat = Literal["mp4", "gif", "png"]


class Plot[Data: DataWithAttrs](ABC):
    class AddHookData(HasHookList): ...

    def __init__(self, renderer: Renderer[Data], data: Data):
        self.renderer = renderer
        self.data = data
        self.hooks: list[Hook] = []

        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return
        self._initialized = True

        initial_data = self._get_initial_data()
        plot_info = self.renderer.init_plot_info()
        self.fig = setup_fig(plot_info)
        init_data = self.renderer.make_init_data(None, self.fig.axes[0], initial_data)

        self.pre_init_fig(init_data)
        self.post_init_fig(init_data)

        self.fig.tight_layout()

    @abstractmethod
    def _get_initial_data(self) -> DataWithAttrs: ...

    def add_hook(self, hook: Hook):
        self.hooks.append(hook)

        post_add_data = Plot.AddHookData(hooks=self.hooks)

        for hook in self.hooks.copy():  # hooks might reorder themselves
            hook.post_add_hook(post_add_data)

    def show(self):
        self._initialize()
        plt.show()

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
