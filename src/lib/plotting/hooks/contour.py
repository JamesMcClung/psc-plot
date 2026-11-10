import numpy as np
from matplotlib.contour import QuadContourSet

from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting.hook import DrawMessage, Hook
from lib.plotting.plot_info import ImageInfo
from lib.scale import LogScale


class Contour(Hook):
    def __init__(self, n_intervals: int):
        self.contours: QuadContourSet | None = None
        self.n_intervals = n_intervals

    def post_init_fig(self, message):
        self._draw(message)

    def post_update_fig(self, message):
        self.contours.remove()
        self._draw(message)

    def _draw(self, message: DrawMessage):
        info = message.plot_info
        assert isinstance(info, ImageInfo)

        if isinstance(info.dim_scales[info.color_dim], LogScale):
            data = np.asarray(info.data)
            positive = data[data > 0]
            levels = np.geomspace(positive.min(), positive.max(), self.n_intervals + 1)
        else:
            levels = np.linspace(np.nanmin(info.data), np.nanmax(info.data), self.n_intervals + 1)
        self.contours = message.axes.contour(
            info.data,
            levels=levels,
            origin="lower",
            extent=(*info.dim_bounds[info.x_dim], *info.dim_bounds[info.y_dim]),
            colors="black",
            linewidths=0.5,
        )

    def get_name_fragments(self) -> list[str]:
        return [f"contour_{self.n_intervals}"]


@arg_parser(
    flags="--contour",
    metavar="n_intervals",
    help="(2d only) draw contours around evenly spaced intervals spanning the data range; logarithmically spaced if the color scale is log",
    dest="hooks",
    nargs="just one",
)
def get(arg: str) -> Contour:
    n_intervals = parse_util.parse_number(arg, "n_intervals", int)
    return Contour(n_intervals)
