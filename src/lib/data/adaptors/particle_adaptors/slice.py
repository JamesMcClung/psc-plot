import pandas as pd

from ....particle_util import PRT_VARIABLES
from ...adaptor import Adaptor
from .. import parse_util
from ..registry import adaptor_parser


class Slice(Adaptor):
    def __init__(self, var_name: str, lower_inclusive: float | None, upper_exclusive: float | None):
        self.var_name = var_name
        self.lower_inclusive = lower_inclusive
        self.upper_exclusive = upper_exclusive

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.lower_inclusive is not None:
            df = df[df[self.var_name] >= self.lower_inclusive]
        if self.upper_exclusive is not None:
            df = df[df[self.var_name] < self.upper_exclusive]
        return df

    def get_name_fragments(self) -> list[str]:
        lower = f"{self.lower_inclusive:.1f}" if self.lower_inclusive is not None else ""
        upper = f"{self.upper_exclusive:.1f}" if self.upper_exclusive is not None else ""
        return [f"slice_{self.var_name}={lower}:{upper}"]


_SLICE_FORMAT = "var_name=lower:upper"


@adaptor_parser(
    "--slice",
    metavar=_SLICE_FORMAT,
    help="restrict data from the given variable to a slice, specified by lower (inclusive) and upper (exclusive) values (both optional)",
)
def parse_slice(arg: str) -> Slice:
    split_arg = arg.split("=")

    if len(split_arg) != 2:
        parse_util.fail_format(arg, _SLICE_FORMAT)

    [var_name, slice_arg] = split_arg

    parse_util.check_value(var_name, "var_name", PRT_VARIABLES)

    split_slice_arg = slice_arg.split(":")
    if len(split_slice_arg) != 2:
        parse_util.fail_format(arg, _SLICE_FORMAT)

    [lower_arg, upper_arg] = split_slice_arg
    lower = parse_util.parse_optional_number(lower_arg, "lower", float)
    upper = parse_util.parse_optional_number(upper_arg, "upper", float)

    parse_util.check_order(lower, upper, "lower", "upper")

    return Slice(var_name, lower, upper)
