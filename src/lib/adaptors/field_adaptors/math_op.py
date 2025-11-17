from typing import Callable

import xarray as xr

from .. import parse_util
from ..adaptor import Adaptor
from ..registry import adaptor_parser


class MathOp(Adaptor[xr.DataArray]):
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

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return self.func(da, self.rhs)

    def get_name_fragments(self) -> list[str]:
        return [f"{self.name_abbrev}_{self.rhs}"]

    def get_modified_var_name(self, title_stem: str) -> str:
        return f"({title_stem}){self.symbol}{{{self.rhs}}}"


op_params = [
    ("pow", "exponent", "raise to the given power", "^", lambda da, rhs: da**rhs),
    ("div", "divisor", "divide by the given value", "/", lambda da, rhs: da / rhs),
    ("mul", "multiplier", "multiply by the given value", "*", lambda da, rhs: da * rhs),
    ("add", "summand", "add the given value", "+", lambda da, rhs: da + rhs),
    ("sub", "subtrahend", "subtract the given value", "-", lambda da, rhs: da - rhs),
]

for name_abbrev, metavar, help, symbol, func in op_params:

    @adaptor_parser(
        f"--{name_abbrev}",
        metavar=metavar,
        help=help,
    )
    def parse(arg: str, *, metavar=metavar, name_abbrev=name_abbrev, symbol=symbol, func=func) -> MathOp:
        # without these default kwargs, the function def captures by reference,
        # so it ends up using the final set of values of the loop,
        # and thus all the parsers would just parse the last kind of math op
        rhs = parse_util.parse_number(arg, metavar, float)
        return MathOp(rhs, name_abbrev, symbol, func)
