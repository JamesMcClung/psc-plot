from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.frame_data_traits import HasAxes, HasData
from lib.plotting.plot import Plot, SaveFormat
from lib.plotting.renderer import Renderer


def print_progress(current_frame: int, n_frames: int):
    current_frame_padded = str(current_frame + 1).rjust(len(str(n_frames)))
    end = "\r" if sys.stdout.isatty() else "\n"
    print(f"frame {current_frame_padded}/{n_frames}", end=end)


class AnimatedPlot[Data: DataWithAttrs](Plot[Data]):
    def __init__(self, renderer: Renderer[Data], data: Data):
        super().__init__(renderer, data)
        self.time_dim: str = self.data.metadata.time_dim

        self.n_frames = len(data.coordss[data.metadata.time_dim])

    @dataclass(kw_only=True)
    class UpdateData(HasData, HasAxes): ...

    def _initialize(self):
        super()._initialize()

        # FIXME get blitting to work with the title
        self.anim = FuncAnimation(self.fig, self._next_frame, frames=self.n_frames, blit=False)

    def _get_initial_data(self) -> DataWithAttrs:
        return self._get_data_at_frame(0)

    def _get_data_at_frame(self, frame: int) -> Data:
        return Idx({self.time_dim: frame}).apply(self.data)

    def _next_frame(self, frame: int):
        frame_data = self._get_data_at_frame(frame)
        update_data = self.UpdateData(axes=self.fig.axes[0], data=frame_data)
        self.pre_update_fig(update_data)
        self.renderer.update_plot_info(frame)
        self.post_update_fig(update_data)
        print_progress(frame, self.n_frames)

    def allowed_save_formats(self) -> list[SaveFormat]:
        return ["mp4", "gif"]

    def save_to_path(self, path: Path, *, dpi: float | None = None):
        self._initialize()
        writer = PillowWriter() if path.suffix == ".gif" else FFMpegWriter()
        self.anim.save(path, writer=writer, dpi=dpi)
