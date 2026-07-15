from lib.config import CONFIG
from lib.data.adaptor import WorldAdaptor
from lib.data.loader import get_loader
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class With(WorldAdaptor):
    def __init__(self, prefix_or_key: str, key: str | None = None):
        self.prefix_or_key = prefix_or_key
        self.key = key

    def apply_world(self, world):
        # case 1: prefix_or_key is a key within the active prefix
        if not self.key and world.active_key and self.prefix_or_key in world.active_data.metadata.var_infos:
            key = self.prefix_or_key
            return world.with_active_data(world.active_data.assign_metadata(active_key=key))

        # case 2: prefix_or_key is a prefix
        prefix = self.prefix_or_key
        key = self.key

        if prefix in world.datas:
            return world.with_active_data(world.active_data.assign_metadata(active_key=key), prefix)

        loader = get_loader(CONFIG.data_dir, prefix, key)
        return loader.apply_world(world)

    def get_name_fragments(self) -> list[str]:
        maybe_prefix = f"{self.prefix_or_key}{SCOPE_OP}" if self.prefix_or_key else ""
        return [f"with_{maybe_prefix}{self.key or ''}"]


SCOPE_OP = "::"
WITH_FORMAT = f"prefix[{SCOPE_OP}[key]] | key"


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
        prefix_or_key = parse_util.parse_identifier(split_arg[0], "prefix | key")
        return With(prefix_or_key)
    else:
        parse_util.fail_format(arg, WITH_FORMAT)
