from typing import Callable

import dask.dataframe as dd
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def float_to_latex_str(f: float) -> str:
    fs = str(f).lower()

    if "e" not in fs:
        return fs

    coefficient, exponent = fs.split("e")
    if coefficient == "1":
        return f"10^{{{exponent}}}"
    return f"{coefficient}\\times10^{{{exponent}}}"


class MathOp(BareAdaptor):
    def __init__(
        self,
        rhs: float,
        name_abbrev: str,
        symbol: str,
        func: Callable[[xr.DataArray, float], xr.DataArray],
    ):
        self.rhs = rhs
        self.name_abbrev = name_abbrev
        self.symbol = symbol
        self.func = func

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return self.func(da, self.rhs)

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return self.func(series, self.rhs)

    def get_name_fragments(self) -> list[str]:
        return [f"{self.name_abbrev}_{self.rhs}"]

    def get_modified_display_latex(self, metadata) -> str:
        return f"({metadata.display_latex}){self.symbol}{{{float_to_latex_str(self.rhs)}}}"


op_params = [
    ("pow", "exponent", "raise to the given power", "^", lambda da, rhs: da**rhs),
    ("div", "divisor", "divide by the given value", "/", lambda da, rhs: da / rhs),
    ("mul", "multiplier", "multiply by the given value", "*", lambda da, rhs: da * rhs),
    ("add", "summand", "add the given value", "+", lambda da, rhs: da + rhs),
    ("sub", "subtrahend", "subtract the given value", "-", lambda da, rhs: da - rhs),
]

for name_abbrev, metavar, help, symbol, func in op_params:

    @arg_parser(
        dest="adaptors",
        flags=f"--{name_abbrev}",
        metavar=metavar,
        help=help,
        nargs="just one",
    )
    def parse(arg: str, *, metavar=metavar, name_abbrev=name_abbrev, symbol=symbol, func=func) -> MathOp:
        # without these default kwargs, the function def captures by reference,
        # so it ends up using the final set of values of the loop,
        # and thus all the parsers would just parse the last kind of math op
        rhs = parse_util.parse_number(arg, metavar, float)
        return MathOp(rhs, name_abbrev, symbol, func)
