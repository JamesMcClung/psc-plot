from __future__ import annotations

import sys
from pathlib import Path

from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

from lib.config import PscPlotConfig
from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.hook import DrawMessage
from lib.plotting.plot import Plot, SaveFormat
from lib.plotting.renderer import Renderer


def print_progress(current_frame: int, n_frames: int):
    current_frame_padded = str(current_frame + 1).rjust(len(str(n_frames)))
    end = "\r" if sys.stdout.isatty() else "\n"
    print(f"frame {current_frame_padded}/{n_frames}", end=end)


class AnimatedPlot(Plot):
    def __init__(self, renderers: list[Renderer[DataWithAttrs]], config: PscPlotConfig, n_frames: int):
        super().__init__(renderers, config)
        self.n_frames = n_frames

    def _initialize(self):
        super()._initialize()

        # FIXME get blitting to work with the title
        self.anim = FuncAnimation(self.fig, self._next_frame, frames=self.n_frames, blit=False)

    def _next_frame(self, frame: int):
        for renderer in self.renderers:
            renderer.update_plot_info(frame)
        self.post_update_fig(DrawMessage(plot_info=self.renderers[0].plot_info, axes=self.fig.axes[0], frame_data=self.renderers[0]._get_data_at_frame(frame)))
        print_progress(frame, self.n_frames)

    def allowed_save_formats(self) -> list[SaveFormat]:
        if self.config.ffmpeg_bin:
            return ["mp4", "gif"]
        else:
            return ["gif"]

    def save_to_path(self, path: Path, *, dpi: float | None = None):
        self._initialize()

        if path.suffix == ".mp4":
            from matplotlib import pyplot as plt

            plt.rcParams["animation.ffmpeg_path"] = str(self.config.ffmpeg_bin)
            writer = FFMpegWriter()
        else:
            writer = PillowWriter()

        self.anim.save(path, writer=writer, dpi=dpi)
