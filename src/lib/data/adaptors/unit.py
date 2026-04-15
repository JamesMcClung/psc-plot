from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, List, Metadata
from lib.parsing.args_registry import arg_parser


class Unit(MetadataAdaptor):
    """Override the unit-LaTeX of the active variable."""

    def __init__(self, var_name: str | None, unit_latex: str):
        self.var_name = var_name
        self.unit_latex = unit_latex

    def apply_field(self, data: Field) -> Field:
        return data

    def apply_list(self, data: List) -> List:
        return data

    def get_modified_unit_latex(self, unit_latex: str, metadata: Metadata) -> str:
        if self.var_name is None or self.var_name == metadata.var_name:
            return self.unit_latex
        return unit_latex

    def get_name_fragments(self) -> list[str]:
        maybe_eq = "=" if self.var_name else ""
        return [f"unit_{self.var_name}{maybe_eq}{self.unit_latex}"]


_UNIT_FORMAT = "[var_name=]unit_latex"


@arg_parser(
    dest="adaptors",
    flags="--unit",
    metavar=_UNIT_FORMAT,
    help=("Override the LaTeX used to render the given quantity's unit. If omitted, defaults to the active variable."),
)
def parse_unit(arg: str) -> Unit:
    if "=" in arg:
        name, value = arg.split("=", 1)
        return Unit(var_name=name, unit_latex=value)
    return Unit(var_name=None, unit_latex=arg)
