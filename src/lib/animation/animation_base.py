from abc import ABC, abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class Animation(ABC):
    def __init__(self, steps: list[int]):
        self.steps = steps
        self.fig, self.ax = plt.subplots()
        self._initialized = False

        # FIXME get blitting to work with the title
        # note: blitting doesn't seem to affect saved animations, only ones displayed with plt.show
        self.anim = FuncAnimation(self.fig, self._update_fig, frames=self.steps, blit=False)

    @abstractmethod
    def _init_fig(self): ...

    @abstractmethod
    def _update_fig(self): ...

    def show(self):
        if not self._initialized:
            self._init_fig()
            self._initialized = True
        plt.show()

    def save(self, path: Path):
        if not self._initialized:
            self._init_fig()
            self._initialized = True
        self.anim.save(path)
