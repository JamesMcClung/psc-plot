from abc import abstractmethod

import numpy as np
import xarray as xr
from scipy.signal import windows

from ....dimension import DIMENSIONS
from ...adaptor import Adaptor
from .. import parse_util
from ..registry import adaptor_parser


class Window(Adaptor):
    allowed_types = [xr.DataArray]

    def __init__(self, dim_name: str):
        self.dim_name = dim_name

    @abstractmethod
    def get_window(self, n_points: int) -> np.ndarray:
        pass

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        dim_idx = da.dims.index(self.dim_name)
        dim_len = da.shape[dim_idx]

        window = self.get_window(dim_len)
        intermediate_shape = [dim_len if d == dim_idx else 1 for d in range(len(da.shape))]
        window = window.reshape(intermediate_shape)

        da = da * window

        return da

    @abstractmethod
    def get_name_fragment_fragment(self) -> str:
        pass

    def get_name_fragments(self) -> list[str]:
        return [f"window_{self.dim_name}={self.get_name_fragment_fragment()}"]


class Kaiser(Window):
    def __init__(self, dim_name: str, beta: float):
        super().__init__(dim_name)
        self.beta = beta

    def get_window(self, n_points: int) -> np.ndarray:
        return windows.kaiser(n_points, self.beta, sym=False)

    def get_name_fragment_fragment(self) -> str:
        return f"kaiser({self.beta})"


KAISER_FORMAT = "dim_name=beta"


@adaptor_parser(
    "--window-kaiser",
    metavar=KAISER_FORMAT,
    help="apply the Kaiser window of the given beta along the given dimension",
)
def parse_window(args: str) -> Window:
    split_args = args.split("=")

    if len(split_args) != 2:
        parse_util.fail_format(args, KAISER_FORMAT)

    [dim_name, beta] = split_args

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)
    beta = parse_util.parse_number(beta, "beta", float)

    return Kaiser(dim_name, beta)
