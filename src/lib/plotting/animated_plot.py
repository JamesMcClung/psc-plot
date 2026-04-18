from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.plot import Plot, SaveFormat
from lib.plotting.renderer import Renderer


def print_progress(current_frame: int, n_frames: int):
    current_frame_padded = str(current_frame + 1).rjust(len(str(n_frames)))
    print(f"frame {current_frame_padded}/{n_frames}", end="\r")


class AnimatedPlot[Data: DataWithAttrs](Plot[Data]):
    def __init__(self, renderer: Renderer[Data], data: Data):
        super().__init__(renderer, data)
        self.time_dim: str = self.data.metadata.time_dim

        self.fig, self.ax = plt.subplots(subplot_kw=renderer.subplot_kw())
        self._initialized = False

        # FIXME get blitting to work with the title
        self.n_frames = len(data.coordss[data.metadata.time_dim])
        self.anim = FuncAnimation(self.fig, self._next_frame, frames=self.n_frames, blit=False)

    def _get_data_at_frame(self, frame: int) -> Data:
        return Idx({self.time_dim: frame}).apply(self.data)

    def _next_frame(self, frame: int):
        frame_data = self._get_data_at_frame(frame)
        update_data = self.renderer.make_update_data(self.ax, frame_data)
        self.pre_update_fig(update_data)
        self.renderer.draw(self.ax, frame_data, update_data)
        self.post_update_fig(update_data)
        print_progress(frame, self.n_frames)

    def _initialize(self):
        if self._initialized:
            return
        self._initialized = True

        frame_0 = self._get_data_at_frame(0)
        init_data = self.renderer.make_init_data(self.fig, self.ax, frame_0)
        self.pre_init_fig(init_data)
        self.renderer.init(self.fig, self.ax, self.data, frame_0, init_data)
        self.post_init_fig(init_data)
        self.fig.tight_layout()

    def show(self):
        self._initialize()
        plt.show()

    def allowed_save_formats(self) -> list[SaveFormat]:
        return ["mp4", "gif"]

    def _save_to_path(self, path: Path):
        self._initialize()
        writer = PillowWriter() if path.suffix == ".gif" else FFMpegWriter()
        self.anim.save(path, writer=writer)
