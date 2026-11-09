import numpy as np
from matplotlib.contour import QuadContourSet

from lib.parsing.args_registry import const_arg
from lib.plotting.hook import DrawMessage, Hook
from lib.plotting.plot_info import ImageInfo

N_INTERVALS = 10


class Contour(Hook):
    def __init__(self):
        self.contours: QuadContourSet | None = None

    def post_init_fig(self, message):
        self._draw(message)

    def post_update_fig(self, message):
        self.contours.remove()
        self._draw(message)

    def _draw(self, message: DrawMessage):
        info = message.plot_info
        assert isinstance(info, ImageInfo)

        levels = np.linspace(np.nanmin(info.data), np.nanmax(info.data), N_INTERVALS + 1)
        self.contours = message.axes.contour(
            info.data,
            levels=levels,
            origin="lower",
            extent=(*info.dim_bounds[info.x_dim], *info.dim_bounds[info.y_dim]),
            colors="black",
            linewidths=0.5,
        )

    def get_name_fragments(self) -> list[str]:
        return ["contour"]


@const_arg(
    flags="--contour",
    help="(2d only) draw contours at 10 evenly spaced intervals spanning the data range",
    dest="hooks",
)
def get() -> Contour:
    return Contour()
