from lib.data.adaptor import Adaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing.args_registry import arg_parser


class With(Adaptor):
    def __init__(self, key: str):
        self.key = key

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        return data.assign_metadata(active_key=self.key)

    def get_name_fragments(self) -> list[str]:
        return [f"with_{self.key}"]


@arg_parser(
    dest="adaptors",
    flags=["--with", "-w"],
    metavar="key",
    help="set the active variable to the given key",
    nargs="just one",
)
def parse_with(arg: str) -> With:
    return With(arg)
