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

        if target not in metadata.var_info and target not in metadata.dims:
            raise ValueError(f"--display target {target!r} is not a known key ({sorted(set(metadata.var_info) | set(metadata.dims))})")

        old_dim = metadata.get_var_info(target)
        new_dim = replace(old_dim, name=Latex(self.value))
        new_dims = {**metadata.dims, target: new_dim} if target in metadata.dims else metadata.dims
        new_var_info = {**metadata.var_info, target: new_dim}

        if target == metadata.var_name:
            return data.assign_metadata(name_fragments=name_fragments, display_latex=self.value, dims=new_dims, var_info=new_var_info)
        return data.assign_metadata(name_fragments=name_fragments, dims=new_dims, var_info=new_var_info)

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
