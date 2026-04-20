import numpy as np
import scipy.stats as stats

from lib.data.adaptors.pos import Pos
from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting.frame_data_traits import (
    HasAxes,
    HasData,
    HasLineType,
    assert_impl,
    check_impl,
)
from lib.plotting.hook import Hook


class Fit(Hook):
    class InitData(HasData, HasAxes): ...

    class UpdateData(HasData, HasAxes): ...

    def __init__(self, subdomain: slice):
        self.subdomain = subdomain

    def pre_init_fig(self, init_data):
        if check_impl(init_data, HasLineType) and init_data.line_type == "-":
            init_data.line_type = "."

    def post_init_fig(self, init_data):
        init_data = assert_impl(init_data, Fit.InitData)

        x_data, y_data = self._get_xy_data(init_data.data)
        fit_y_data, label = self._get_fit_y_data(x_data, y_data)
        [self.line] = init_data.axes.plot(x_data, fit_y_data, "--", label=label)

        init_data.axes.legend()

    def post_update_fig(self, update_data):
        update_data = assert_impl(update_data, Fit.UpdateData)

        x_data, y_data = self._get_xy_data(update_data.data)
        fit_y_data, label = self._get_fit_y_data(x_data, y_data)
        self.line.set_data(x_data, fit_y_data)
        self.line.set_label(label)

        update_data.axes.legend()  # in case label changed

    def _get_fit_y_data(self, x_data: np.ndarray, y_data: np.ndarray) -> tuple[np.ndarray, str]:
        x_log = np.log(x_data)
        y_log = np.log(y_data)

        [slope, intercept, rvalue, *_] = stats.linregress(x_log, y_log)

        y_fit_log = x_log * slope + intercept
        y_fit = np.exp(y_fit_log)

        label = f"$\\gamma={-slope:.3f}$ ($r^2={rvalue**2:.3f}$)"

        return y_fit, label

    def _get_xy_data(self, data: DataWithAttrs) -> tuple[np.ndarray, np.ndarray]:
        spatial_dim = data.metadata.spatial_dims[0]
        slicer = Pos({spatial_dim: self.subdomain})
        data = slicer.apply(data)
        if isinstance(data, Field):
            return (data.coordss[spatial_dim], data.active_data)
        elif isinstance(data, List):
            return (data.data[spatial_dim], data.data[data.metadata.spatial_dims[1]])


@arg_parser(
    flags="--fit",
    metavar="lower:upper",
    help="(1d only) fit the data to a power law on the given subdomain",
    dest="hooks",
)
def parse_fit(arg: str) -> Fit:
    subdomain = parse_util.parse_slice(arg, float)
    return Fit(subdomain)
