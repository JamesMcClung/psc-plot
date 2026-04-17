import typing

import numpy as np
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class ReduceFunc(typing.Protocol):
    def __call__(self, da: xr.DataArray, dim_names: list[str]) -> xr.DataArray: ...


class ModifyDisplayLatex(typing.Protocol):
    def __call__(self, display_latex: str, dim_names: list[str]) -> str: ...


REDUCE_FUNCS: dict[str, tuple[ReduceFunc, ModifyDisplayLatex]] = {
    "mean": (
        lambda da, dim_names: da.reduce(np.nanmean, dim_names),
        lambda display_latex, dim_names: f"\\langle {display_latex}\\rangle_{{{','.join(dim_names)}}}",
    ),
    "integrate": (
        lambda da, dim_names: da.integrate(dim_names),
        lambda display_latex, dim_names: f"\\int \\text{{d}}{'\\text{d}'.join(dim_names)}\\,({display_latex})",
    ),
    "max": (
        lambda da, dim_names: da.max(dim_names, skipna=True),
        lambda display_latex, dim_names: f"\\max_{{{','.join(dim_names)}}}({display_latex})",
    ),
    "min": (
        lambda da, dim_names: da.min(dim_names, skipna=True),
        lambda display_latex, dim_names: f"\\min_{{{','.join(dim_names)}}}({display_latex})",
    ),
}


class Reduce(BareAdaptor):
    def __init__(self, dim_names: str | list[str], func_name: str):
        self.dim_names = [dim_names] if isinstance(dim_names, str) else dim_names
        self.func_name = func_name

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        if not self.dim_names:
            return da
        return REDUCE_FUNCS[self.func_name][0](da, self.dim_names)

    def get_modified_display_latex(self, metadata) -> str:
        if not self.dim_names:
            return metadata.display_latex
        return REDUCE_FUNCS[self.func_name][1](metadata.display_latex, self.dim_names)

    def get_name_fragments(self) -> list[str]:
        if not self.dim_names:
            return []
        return [f"reduce_{','.join(self.dim_names)}={self.func_name}"]


REDUCE_FORMAT = "dim_name[,dim_name ...]=reduce_func"


@arg_parser(
    dest="adaptors",
    flags="--reduce",
    metavar=REDUCE_FORMAT,
    help="reduce the given dimension(s) via the given method",
)
def parse_reduce(arg: str) -> Reduce:
    [dim_names_arg, func_name] = parse_util.parse_assignment(arg, REDUCE_FORMAT)

    dim_names = parse_util.parse_comma_separated_list(dim_names_arg)

    for dim_name in dim_names:
        parse_util.check_identifier(dim_name, "dim_name")

    parse_util.check_value(func_name, "reduce_func", REDUCE_FUNCS)

    return Reduce(dim_names, func_name)
