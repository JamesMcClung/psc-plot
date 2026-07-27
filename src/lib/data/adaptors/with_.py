from lib.config import _DATA_DIR_KEY
from lib.data.adaptor import WorldAdaptor
from lib.data.loader import get_loader
from lib.file_util import Prepath
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class With(WorldAdaptor):
    def __init__(self, prepath: Prepath | None, key: str | None = None):
        self.prepath = prepath
        self.key = key

    def apply_world(self, world):
        if not self.prepath:
            return world.with_active_data(world.active_data.assign_metadata(active_key=self.key))

        if self.prepath in world.datas:
            return world.with_active_data(world.datas[self.prepath].assign_metadata(active_key=self.key), self.prepath)

        loader = get_loader(world.config.data_root, self.prepath, self.key)
        return loader.apply_world(world)

    def get_name_fragments(self) -> list[str]:
        maybe_prepath = f"{self.prepath}{SCOPE_OP}" if self.prepath else ""
        return [f"with_{maybe_prepath}{self.key or ''}"]


SCOPE_OP = "::"
WITH_FORMAT = f"[prepath{SCOPE_OP}][var_key]"


@arg_parser(
    dest="adaptors",
    flags=["--with", "-w"],
    metavar=WITH_FORMAT,
    help=f"Switch to a different prepath (e.g. `run1/pfd`, relative to {_DATA_DIR_KEY}) and/or variable (e.g. `ey_ec`).",
    nargs="just one",
)
def parse_with(arg: str) -> With:
    split_arg = arg.split(SCOPE_OP)

    if len(split_arg) == 2:
        [prepath, key_arg] = split_arg
    elif len(split_arg) == 1:
        prepath = None
        [key_arg] = split_arg
    else:
        parse_util.fail_format(arg, WITH_FORMAT)

    key = parse_util.parse_optional_identifier(key_arg, "key")
    return With(prepath, key)
