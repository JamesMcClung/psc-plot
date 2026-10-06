from __future__ import annotations

import os
import sys
from pathlib import Path

from matplotlib.animation import AbstractMovieWriter, FFMpegWriter, FuncAnimation, PillowWriter

from lib.config import PscPlotConfig
from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.hook import DrawMessage
from lib.plotting.plot import Plot, SaveFormat
from lib.plotting.renderer import Renderer
from lib.profiling.profiler import FRAME_REDRAW, FRAME_RENDER, FRAME_UPDATE, profile_stage


def print_progress(current_frame: int, n_frames: int):
    current_frame_padded = str(current_frame + 1).rjust(len(str(n_frames)))
    end = "\r" if sys.stdout.isatty() else "\n"
    print(f"frame {current_frame_padded}/{n_frames}", end=end)


class _DiscardingWriter(AbstractMovieWriter):
    """Draws each frame and keeps nothing: renders an animation without encoding it."""

    def setup(self, fig, outfile, dpi=None):
        super().setup(fig, outfile, dpi)

    def grab_frame(self, **savefig_kwargs):
        self.fig.canvas.draw()

    def finish(self):
        pass


class AnimatedPlot(Plot):
    def __init__(self, renderers: list[Renderer[DataWithAttrs]], config: PscPlotConfig, n_frames: int):
        super().__init__(renderers, config)
        self.n_frames = n_frames

    def _initialize(self):
        super()._initialize()

        # FIXME get blitting to work with the title
        self.anim = FuncAnimation(self.fig, self._next_frame, frames=self.n_frames, blit=False)

    def _next_frame(self, frame: int):
        with profile_stage(FRAME_UPDATE):
            for renderer in self.renderers:
                renderer.update_plot_info(frame)
            self.grid.update()
            self.post_update_fig(DrawMessage(plot_info=self.renderers[0].plot_info, axes=self.fig.axes[0], frame_data=self.renderers[0]._get_data_at_frame(frame)))
        print_progress(frame, self.n_frames)

    def allowed_save_formats(self) -> list[SaveFormat]:
        if self.config.ffmpeg_bin:
            return ["mp4", "gif"]
        else:
            return ["gif"]

    def save_to_path(self, path: Path, *, dpi: float | None = None):
        if path.suffix == ".mp4":
            from matplotlib import pyplot as plt

            plt.rcParams["animation.ffmpeg_path"] = str(self.config.ffmpeg_bin)
            writer = FFMpegWriter()
        else:
            writer = PillowWriter()

        self._run_writer(path, writer, dpi)

    def render_offscreen(self):
        # the same anim.save path as a real save, so offscreen and saved profiles are comparable
        self._run_writer(Path(os.devnull), _DiscardingWriter(), None)

    def _run_writer(self, path: Path, writer: AbstractMovieWriter, dpi: float | None):
        self._initialize()

        grab_frame = writer.grab_frame

        def profiled_grab_frame(**savefig_kwargs):
            with profile_stage(FRAME_RENDER):
                grab_frame(**savefig_kwargs)

        writer.grab_frame = profiled_grab_frame

        # After each frame, matplotlib calls _post_draw -> draw_idle, which on Agg is a full synchronous draw on top of grab_frame's.
        post_draw = self.anim._post_draw

        def profiled_post_draw(*args, **kwargs):
            with profile_stage(FRAME_REDRAW):
                post_draw(*args, **kwargs)

        self.anim._post_draw = profiled_post_draw
        self.anim.save(path, writer=writer, dpi=dpi)
