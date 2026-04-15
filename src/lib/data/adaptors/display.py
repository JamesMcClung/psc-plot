from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, List, Metadata
from lib.parsing.args_registry import arg_parser


class Display(MetadataAdaptor):
    """Override the display-LaTeX of the active variable."""

    def __init__(self, target: str | None, value: str):
        self.target = target
        self.value = value

    def apply_field(self, data: Field) -> Field:
        return data

    def apply_list(self, data: List) -> List:
        return data

    def get_modified_display_latex(self, display_latex: str, metadata: Metadata) -> str:
        if self.target is None or self.target == metadata.var_name:
            return self.value
        return display_latex

    def get_name_fragments(self) -> list[str]:
        return [f"display_{self.target or 'active'}={self.value}"]


_DISPLAY_FORMAT = "[var_name=]display_latex"


@arg_parser(
    dest="adaptors",
    flags="--display",
    metavar=_DISPLAY_FORMAT,
    help=("Override the LaTeX used to render the given quantity's name. If omitted, defaults to the active variable."),
)
def parse_display(arg: str) -> Display:
    if "=" in arg:
        name, value = arg.split("=", 1)
        return Display(target=name, value=value)
    return Display(target=None, value=arg)
