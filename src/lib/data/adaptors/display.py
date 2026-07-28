from lib.data.adaptor import Adaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing.args_registry import arg_parser


class Display(Adaptor):
    """Override the display-LaTeX of the active variable or of a dimension."""

    def __init__(self, key: str | None, display: str):
        self.key = key
        self.display = display

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        metadata = data.metadata

        key = self.key or metadata.active_key
        if key is None:
            raise ValueError("--display requires a target; specify a variable as a positional argument or use --display TARGET=VALUE")

        if key not in metadata.var_infos:
            raise ValueError(f"--display target {key!r} is not a known key ({sorted(metadata.var_infos)})")

        info = metadata.var_infos[key].assign(display=self.display)
        return data.with_info(key, info)

    def get_name_fragments(self) -> list[str]:
        return [f"display_{self.key or 'active'}={self.display}"]


_DISPLAY_FORMAT = "[name=]display_latex"


@arg_parser(
    dest="adaptors",
    flags="--display",
    metavar=_DISPLAY_FORMAT,
    help=("Override the LaTeX used to render the given quantity's name. The name may be the active variable (default) or a dimension name."),
)
def parse_display(arg: str) -> Display:
    if "=" in arg:
        key, display = arg.split("=", 1)
        return Display(key=key, display=display)
    return Display(key=None, display=arg)
