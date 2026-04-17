from __future__ import annotations

import typing
from abc import abstractmethod
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.plot import Plot


def print_progress(current_frame: int, n_frames: int):
    current_frame_padded = str(current_frame + 1).rjust(len(str(n_frames)))
    print(f"frame {current_frame_padded}/{n_frames}", end="\r")


class AnimatedPlot[Data: DataWithAttrs](Plot[Data]):
    def __init__(
        self,
        data: Data,
        *,
        subplot_kw: dict[str, typing.Any] = {},
    ):
        super().__init__(data)
        # TODO: don't bother setting these?
        self.spatial_dims = self.data.metadata.spatial_dims
        self.time_dim: str = self.data.metadata.time_dim

        self.fig, self.ax = plt.subplots(subplot_kw=subplot_kw)
        self._initialized = False

        # FIXME get blitting to work with the title
        # note: blitting doesn't seem to affect saved animations, only ones displayed with plt.show
        self.n_frames = len(data.coordss[data.metadata.time_dim])
        self.anim = FuncAnimation(self.fig, self._next_frame, frames=self.n_frames, blit=False)

    def _get_data_at_frame(self, frame: int) -> Data:
        return Idx({self.time_dim: frame}).apply(self.data)

    @abstractmethod
    def _init_fig(self): ...

    @abstractmethod
    def _update_fig(self, frame: int): ...

    def _next_frame(self, frame: int):
        self._update_fig(frame)
        print_progress(frame, self.n_frames)

    def _initialize(self):
        if not self._initialized:
            self._init_fig()
            self._initialized = True

    def show(self):
        self._initialize()
        plt.show()

    def _get_save_ext(self):
        return ".mp4"

    def _save_to_path(self, path: Path):
        self._initialize()
        writer = PillowWriter() if path.suffix == ".gif" else FFMpegWriter()
        self.anim.save(path, writer=writer)
