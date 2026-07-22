import numpy as np
import scipy.stats as stats

from lib.data.adaptors.pos import Pos
from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting.hook import Hook
from lib.plotting.plot_info import LineInfo, ScatterInfo


class Fit(Hook):
    def __init__(self, subdomain: slice):
        self.subdomain = subdomain

    def post_init_fig(self, message):
        if isinstance(message.plot_info, LineInfo) and message.plot_info.line_style == "-":
            message.plot_info.set("line_style", ".")

        assert isinstance(message.plot_info, (LineInfo, ScatterInfo))

        x_data, y_data = self._get_xy_data(message.frame_data, message.plot_info.x_dim, message.plot_info.y_dim)
        fit_y_data, label = self._get_fit_y_data(x_data, y_data)
        [self.line] = message.axes.plot(x_data, fit_y_data, "--", label=label, scalex=False, scaley=False)

        message.axes.legend()

    def post_update_fig(self, message):
        assert isinstance(message.plot_info, (LineInfo, ScatterInfo))

        x_data, y_data = self._get_xy_data(message.frame_data, message.plot_info.x_dim, message.plot_info.y_dim)
        fit_y_data, label = self._get_fit_y_data(x_data, y_data)
        self.line.set_data(x_data, fit_y_data)
        self.line.set_label(label)

        message.axes.legend()  # in case label changed

    def _get_fit_y_data(self, x_data: np.ndarray, y_data: np.ndarray) -> tuple[np.ndarray, str]:
        x_log = np.log(x_data)
        y_log = np.log(y_data)

        [slope, intercept, rvalue, *_] = stats.linregress(x_log, y_log)

        y_fit_log = x_log * slope + intercept
        y_fit = np.exp(y_fit_log)

        label = f"$\\gamma={-slope:.3f}$ ($r^2={rvalue**2:.3f}$)"

        return y_fit, label

    def _get_xy_data(self, data: DataWithAttrs, x_dim: str, y_dim: str) -> tuple[np.ndarray, np.ndarray]:
        slicer = Pos({x_dim: self.subdomain})
        data = slicer.apply(data)
        if isinstance(data, Field):
            return (data.coordss[x_dim], data.data[y_dim])
        elif isinstance(data, List):
            return (data.data[x_dim], data.data[y_dim])


@arg_parser(
    flags="--fit",
    metavar="lower:upper",
    help="(1d only) fit the data to a power law on the given subdomain",
    dest="hooks",
)
def parse_fit(arg: str) -> Fit:
    subdomain = parse_util.parse_slice(arg, float)
    return Fit(subdomain)
