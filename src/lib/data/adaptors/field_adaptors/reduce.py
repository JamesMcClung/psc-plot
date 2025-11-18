import typing

import numpy as np
import xarray as xr

from ....dimension import DIMENSIONS
from .. import parse_util
from ..adaptor import Adaptor
from ..registry import adaptor_parser


class ReduceFunc(typing.Protocol):
    def __call__(self, da: xr.DataArray, dim_name: str) -> xr.DataArray: ...


REDUCE_FUNCS: dict[str, ReduceFunc] = {
    "mean": lambda da, dim_name: da.reduce(np.nanmean, dim_name),
    "integrate": lambda da, dim_name: da.integrate(dim_name),
}


class Reduce(Adaptor):
    def __init__(self, dim_name: str, func_name: str):
        self.dim_name = dim_name
        self.func_name = func_name

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return REDUCE_FUNCS[self.func_name](da, self.dim_name)

    def get_name_fragments(self) -> list[str]:
        return ["reduce_{self.dim_name}={self.func_name}"]


REDUCE_FORMAT = "dim_name=reduce_func"


@adaptor_parser(
    "--reduce",
    metavar=REDUCE_FORMAT,
    help="reduce the given dimension using the given method",
)
def parse_reduce(args: str) -> Reduce:
    split_args = args.split("=")

    if len(split_args) != 2:
        parse_util.fail_format(args, REDUCE_FORMAT)

    [dim_name, func_name] = split_args

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)
    parse_util.check_value(func_name, "reduce_func", REDUCE_FUNCS)

    return Reduce(dim_name, func_name)
