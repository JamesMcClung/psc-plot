from abc import ABC, abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from . import plt_util
from . import xr_util

__all__ = ["Animation", "BpAnimation"]


class Animation(ABC):
    def __init__(self, steps: list[int]):
        self.steps = steps
        self.fig, self.ax = plt.subplots()

        self._init_fig()

        # FIXME get blitting to work with the title
        # note: blitting doesn't seem to affect saved animations, only ones displayed with plt.show
        self.anim = FuncAnimation(self.fig, self._update_fig, frames=steps, blit=False)

    @abstractmethod
    def _init_fig(self): ...

    @abstractmethod
    def _update_fig(self): ...

    def show(self):
        plt.show()

    def save(self, path: Path):
        self.anim.save(path)


class BpAnimation(Animation):
    def __init__(self, steps: list[int], bp_name: str, var: str):
        self.bp_name = bp_name
        self.var = var
        super().__init__(steps)

    def _init_fig(self):
        ds = xr_util.load_ds(self.bp_name, self.steps[0])
        im_data = xr_util.get_im_data(ds, self.var)

        self.im = self.ax.imshow(im_data)

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        plt_util.update_title(self.ax, self.var, ds.time)
        self.ax.set_xlabel("y index")
        self.ax.set_ylabel("z index")

    def _update_fig(self, step: int):
        ds = xr_util.load_ds(self.bp_name, step)
        im_data = xr_util.get_im_data(ds, self.var)

        self.im.set_array(im_data)
        plt_util.update_title(self.ax, self.var, ds.time)
        plt_util.update_cbar(self.im)
        return [self.im, self.ax.title]
