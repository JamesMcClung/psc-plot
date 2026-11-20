from pathlib import Path

from lib.plotting.plot import Plot, SaveFormat
from lib.profiling.profiler import FRAME_RENDER, profile_stage


class StaticPlot(Plot):
    def allowed_save_formats(self) -> list[SaveFormat]:
        return ["png"]

    def save_to_path(self, path: Path):
        self._initialize()
        with profile_stage(FRAME_RENDER):
            self.fig.savefig(path, dpi="figure")

    def render_offscreen(self, max_frames: int | None = None):
        self._initialize()
        with profile_stage(FRAME_RENDER):
            self.fig.canvas.draw()
