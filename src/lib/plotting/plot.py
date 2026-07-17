from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from matplotlib import pyplot as plt

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.hook import DrawMessage, Hook
from lib.plotting.renderer import Renderer
from lib.plotting.setup_fig import setup_fig

type SaveFormat = Literal["mp4", "gif", "png"]


class Plot(ABC):
    def __init__(self, renderers: list[Renderer[DataWithAttrs]]):
        self.renderers = renderers
        self.hooks: list[Hook] = []

        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return
        self._initialized = True

        self.fig = setup_fig([r.plot_info for r in self.renderers])
        # TODO hooks should be per-renderer; for now, just apply them to the 1st one
        self.post_init_fig(DrawMessage(plot_info=self.renderers[0].plot_info, axes=self.fig.axes[0], frame_data=self.renderers[0]._get_data_at_frame(0)))

        self.fig.tight_layout()

    def add_hook(self, hook: Hook):
        self.hooks.append(hook)

    def show(self):
        self._initialize()
        plt.show()

    @abstractmethod
    def save_to_path(self, path: Path, *, dpi: float | None = None): ...

    @abstractmethod
    def allowed_save_formats(self) -> list[SaveFormat]: ...

    def default_save_format(self) -> SaveFormat:
        return self.allowed_save_formats()[0]

    def post_init_fig(self, message: DrawMessage):
        for hook in self.hooks:
            hook.post_init_fig(message)

    def post_update_fig(self, message: DrawMessage):
        for hook in self.hooks:
            hook.post_update_fig(message)
