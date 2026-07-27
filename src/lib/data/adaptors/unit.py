from lib.data.adaptor import Adaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing.args_registry import arg_parser


class Unit(Adaptor):
    """Override the unit-LaTeX of the active variable or of a dimension."""

    def __init__(self, key: str | None, unit: str):
        self.key = key
        self.unit = unit

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        metadata = data.metadata

        key = self.key or metadata.active_key
        if key is None:
            raise ValueError("--unit requires a target; specify a variable as a positional argument or use --unit TARGET=VALUE")

        if key not in metadata.var_infos:
            raise ValueError(f"--unit target {key!r} is not a known key ({sorted(metadata.var_infos)})")

        info = metadata.var_infos[key].assign(unit=self.unit)
        return data.with_info(key, info)

    def get_name_fragments(self) -> list[str]:
        return [f"unit_{self.key or 'active'}={self.unit}"]


_UNIT_FORMAT = "[name=]unit_latex"


@arg_parser(
    dest="adaptors",
    flags="--unit",
    metavar=_UNIT_FORMAT,
    help=("Override the LaTeX used to render the given quantity's unit. The name may be the active variable (default) or a dimension name."),
)
def parse_unit(arg: str) -> Unit:
    if "=" in arg:
        key, unit = arg.split("=", 1)
        return Unit(key=key, unit=unit)
    return Unit(key=None, unit=arg)
