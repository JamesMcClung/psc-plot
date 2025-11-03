import typing
from abc import ABC, abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class Animation(ABC):
    def __init__(self, steps: list[int], *, subplot_kw: dict[str, typing.Any] = {}):
        self.steps = steps
        self.fig, self.ax = plt.subplots(subplot_kw=subplot_kw)
        self._initialized = False

        # FIXME get blitting to work with the title
        # note: blitting doesn't seem to affect saved animations, only ones displayed with plt.show
        self.anim = FuncAnimation(self.fig, self._update_fig, frames=self.steps, blit=False)

    @abstractmethod
    def _init_fig(self): ...

    @abstractmethod
    def _update_fig(self): ...

    @abstractmethod
    def _get_default_save_path(self) -> str: ...

    def show(self):
        if not self._initialized:
            self._init_fig()
            self._initialized = True
        plt.show()

    def save(self, path_override: Path | None = None):
        if not self._initialized:
            self._init_fig()
            self._initialized = True
        path = path_override or self._get_default_save_path()
        self.anim.save(path)
