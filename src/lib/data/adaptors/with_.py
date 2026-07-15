from lib.config import CONFIG
from lib.data.adaptor import Adaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.data.loader import discover_loaders
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class With(Adaptor):
    def __init__(self, prefix: str | None, key: str | None):
        self.prefix = prefix
        self.key = key

    def apply_world(self, world):
        if self.prefix:
            if self.prefix not in world.datas:
                loaders = discover_loaders(CONFIG.data_dir)
                data = loaders[self.prefix](self.prefix, self.key).get_data()
            else:
                data = world.active_data

            world = world.with_active_data(data, active_key=self.prefix)

        return super().apply_world(world)

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        return data.assign_metadata(active_key=self.key)

    def get_name_fragments(self) -> list[str]:
        maybe_prefix = f"{self.prefix}{SCOPE_OP}" if self.prefix else ""
        return [f"with_{maybe_prefix}{self.key or ''}"]


SCOPE_OP = "::"
WITH_FORMAT = f"prefix{SCOPE_OP}[key] | key"


@arg_parser(
    dest="adaptors",
    flags=["--with", "-w"],
    metavar=WITH_FORMAT,
    help="switch to a different prefix and/or variable",
    nargs="just one",
)
def parse_with(arg: str) -> With:
    split_arg = arg.split(SCOPE_OP)

    if len(split_arg) == 2:
        prefix = parse_util.parse_identifier(split_arg[0], "prefix")
        key = parse_util.parse_optional_identifier(split_arg[1] or None, "key")
        return With(prefix, key)
    elif len(split_arg) == 1:
        prefix = None
        key = parse_util.parse_identifier(split_arg[0], "key")
    else:
        parse_util.fail_format(arg, WITH_FORMAT)

    return With(prefix, key)
