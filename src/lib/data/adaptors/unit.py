from lib.data.adaptor import Adaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing.args_registry import arg_parser


class Unit(Adaptor):
    """Override the unit-LaTeX of the active variable or of a dimension."""

    def __init__(self, target: str | None, value: str):
        self.target = target
        self.value = value

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        metadata = data.metadata
        name_fragments = metadata.name_fragments + self.get_name_fragments()

        target = self.target or metadata.active_key
        if target is None:
            raise ValueError("--unit requires a target; specify a variable as a positional argument or use --unit TARGET=VALUE")

        if target not in metadata.var_info:
            raise ValueError(f"--unit target {target!r} is not a known key ({sorted(metadata.var_info)})")

        old_dim = metadata.var_info[target]
        new_dim = old_dim.assign(unit=self.value)
        new_var_info = {**metadata.var_info, target: new_dim}
        return data.assign_metadata(name_fragments=name_fragments, var_info=new_var_info)

    def get_name_fragments(self) -> list[str]:
        return [f"unit_{self.target or 'active'}={self.value}"]


_UNIT_FORMAT = "[name=]unit_latex"


@arg_parser(
    dest="adaptors",
    flags="--unit",
    metavar=_UNIT_FORMAT,
    help=("Override the LaTeX used to render the given quantity's unit. The name may be the active variable (default) or a dimension name."),
)
def parse_unit(arg: str) -> Unit:
    if "=" in arg:
        name, value = arg.split("=", 1)
        return Unit(target=name, value=value)
    return Unit(target=None, value=arg)
