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

        if self.target is None or self.target == metadata.var_name:
            return data.assign_metadata(name_fragments=name_fragments, display_latex=self.value)

        if self.target in metadata.dims:
            old_dim = metadata.dims[self.target]
            new_dim = replace(old_dim, name=Latex(self.value))
            new_dims = {**metadata.dims, self.target: new_dim}
            return data.assign_metadata(name_fragments=name_fragments, dims=new_dims)

        raise ValueError(f"--display target {self.target!r} is neither the active variable ({metadata.var_name!r}) nor a known dimension ({sorted(metadata.dims)})")

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
