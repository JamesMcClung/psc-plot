from dataclasses import replace

from lib.data.adaptor import Adaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.latex import Latex
from lib.parsing.args_registry import arg_parser


class Display(Adaptor):
    """Override the display-LaTeX of the active variable or of a dimension."""

    def __init__(self, target: str | None, value: str):
        self.target = target
        self.value = value

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        metadata = data.metadata
        name_fragments = metadata.name_fragments + self.get_name_fragments()

        target = self.target or metadata.var_name
        if target is None:
            raise ValueError("--display requires a target; specify a variable as a positional argument or use --display TARGET=VALUE")

        if target not in metadata.var_info:
            raise ValueError(f"--display target {target!r} is not a known key ({sorted(metadata.var_info)})")

        old_dim = metadata.var_info[target]
        new_dim = replace(old_dim, name=Latex(self.value))
        new_var_info = {**metadata.var_info, target: new_dim}
        return data.assign_metadata(name_fragments=name_fragments, var_info=new_var_info)

    def get_name_fragments(self) -> list[str]:
        return [f"display_{self.target or 'active'}={self.value}"]


_DISPLAY_FORMAT = "[name=]display_latex"


@arg_parser(
    dest="adaptors",
    flags="--display",
    metavar=_DISPLAY_FORMAT,
    help=("Override the LaTeX used to render the given quantity's name. The name may be the active variable (default) or a dimension name."),
)
def parse_display(arg: str) -> Display:
    if "=" in arg:
        name, value = arg.split("=", 1)
        return Display(target=name, value=value)
    return Display(target=None, value=arg)
