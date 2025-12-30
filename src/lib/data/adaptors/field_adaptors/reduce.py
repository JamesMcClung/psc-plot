import typing

import numpy as np
import xarray as xr

from lib.data.adaptor import BareAdaptor

from ....dimension import DIMENSIONS
from .. import parse_util
from ..registry import adaptor_parser


class ReduceFunc(typing.Protocol):
    def __call__(self, da: xr.DataArray, dim_names: list[str]) -> xr.DataArray: ...


class ModifyVarLatex(typing.Protocol):
    def __call__(self, var_latex: str, dim_names: list[str]) -> str: ...


REDUCE_FUNCS: dict[str, tuple[ReduceFunc, ModifyVarLatex]] = {
    "mean": (
        lambda da, dim_names: da.reduce(np.nanmean, dim_names),
        lambda var_latex, dim_names: f"\\langle{var_latex}\\rangle_{{{','.join(dim_names)}}}",
    ),
    "integrate": (
        lambda da, dim_names: da.integrate(dim_names),
        lambda var_latex, dim_names: f"\\int \\text{{d}}{'\\text{d}'.join(dim_names)}\\,({var_latex})",
    ),
    "max": (
        lambda da, dim_names: da.max(dim_names, skipna=True),
        lambda var_latex, dim_names: f"\\max_{{{','.join(dim_names)}}}({var_latex})",
    ),
    "min": (
        lambda da, dim_names: da.min(dim_names, skipna=True),
        lambda var_latex, dim_names: f"\\min_{{{','.join(dim_names)}}}({var_latex})",
    ),
}


class Reduce(BareAdaptor):
    def __init__(self, dim_names: str | list[str], func_name: str):
        self.dim_names = [dim_names] if isinstance(dim_names, str) else dim_names
        self.func_name = func_name

    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return REDUCE_FUNCS[self.func_name][0](da, self.dim_names)

    def get_modified_var_latex(self, var_latex: str) -> str:
        return REDUCE_FUNCS[self.func_name][1](var_latex, self.dim_names)

    def get_name_fragments(self) -> list[str]:
        return [f"reduce_{','.join(self.dim_names)}={self.func_name}"]


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
