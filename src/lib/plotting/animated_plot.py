from __future__ import annotations

import sys
from pathlib import Path

from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.hook import DrawMessage
from lib.plotting.plot import Plot, SaveFormat
from lib.plotting.renderer import Renderer


def print_progress(current_frame: int, n_frames: int):
    current_frame_padded = str(current_frame + 1).rjust(len(str(n_frames)))
    end = "\r" if sys.stdout.isatty() else "\n"
    print(f"frame {current_frame_padded}/{n_frames}", end=end)


class AnimatedPlot(Plot):
    def __init__(self, renderer: Renderer[DataWithAttrs], n_frames: int):
        super().__init__(renderer)
        self.n_frames = n_frames

    def _initialize(self):
        super()._initialize()

        # FIXME get blitting to work with the title
        self.anim = FuncAnimation(self.fig, self._next_frame, frames=self.n_frames, blit=False)

    def _next_frame(self, frame: int):
        self.renderer.update_plot_info(frame)
        self.post_update_fig(DrawMessage(plot_info=self.renderer.plot_info, axes=self.fig.axes[0], frame_data=self.renderer._get_data_at_frame(frame)))
        print_progress(frame, self.n_frames)

    def allowed_save_formats(self) -> list[SaveFormat]:
        return ["mp4", "gif"]

    def save_to_path(self, path: Path, *, dpi: float | None = None):
        self._initialize()
        writer = PillowWriter() if path.suffix == ".gif" else FFMpegWriter()
        self.anim.save(path, writer=writer, dpi=dpi)
