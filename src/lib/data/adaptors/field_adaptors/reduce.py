import typing

import numpy as np
import xarray as xr

from lib.data.adaptor import BareAdaptor

from ....dimension import DIMENSIONS
from .. import parse_util
from ..registry import adaptor_parser


class ReduceFunc(typing.Protocol):
    def __call__(self, da: xr.DataArray, dim_name: str) -> xr.DataArray: ...


class ModifyVarLatex(typing.Protocol):
    def __call__(self, var_latex: str, dim_name: str) -> str: ...


REDUCE_FUNCS: dict[str, tuple[ReduceFunc, ModifyVarLatex]] = {
    "mean": (
        lambda da, dim_name: da.reduce(np.nanmean, dim_name),
        lambda var_latex, dim_name: f"\\langle{var_latex}\\rangle_{{{dim_name}}}",
    ),
    "integrate": (
        lambda da, dim_name: da.integrate(dim_name),
        lambda var_latex, dim_name: f"\\int \\text{{d}}{dim_name}\\,({var_latex})",
    ),
    "max": (
        lambda da, dim_name: da.max(dim_name, skipna=True),
        lambda var_latex, dim_name: f"\\max_{{{dim_name}}}({var_latex})",
    ),
    "min": (
        lambda da, dim_name: da.min(dim_name, skipna=True),
        lambda var_latex, dim_name: f"\\min_{{{dim_name}}}({var_latex})",
    ),
}


class Reduce(BareAdaptor):
    def __init__(self, dim_name: str, func_name: str):
        self.dim_name = dim_name
        self.func_name = func_name

    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return REDUCE_FUNCS[self.func_name][0](da, self.dim_name)

    def get_modified_var_latex(self, var_latex: str) -> str:
        return REDUCE_FUNCS[self.func_name][1](var_latex, self.dim_name)

    def get_name_fragments(self) -> list[str]:
        return [f"reduce_{self.dim_name}={self.func_name}"]


REDUCE_FORMAT = "dim_name=reduce_func"


@adaptor_parser(
    "--reduce",
    metavar=REDUCE_FORMAT,
    help="reduce the given dimension using the given method",
)
def parse_reduce(arg: str) -> Reduce:
    [dim_name, func_name] = parse_util.parse_assignment(arg, REDUCE_FORMAT)

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)
    parse_util.check_value(func_name, "reduce_func", REDUCE_FUNCS)

    return Reduce(dim_name, func_name)
