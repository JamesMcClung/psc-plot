from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def _get_default_new_key(data: DataWithAttrs, old_key: str) -> str:
    new_key_base = old_key + "_copy"
    n_copies = 1
    while (new_key := new_key_base + str(n_copies)) in data.metadata.var_infos:
        n_copies += 1
    return new_key


class Copy(WorldAdaptor):
    def __init__(self, new_key: str | None, old_key: str):
        self.new_key = new_key
        self.old_key = old_key

    def apply_world(self, world):
        active = world.require_active_data()
        old = active[self.old_key]
        old_info = active.metadata.var_infos[self.old_key]
        new_key = self.new_key or _get_default_new_key(active, self.old_key)
        return world.with_active(data=active.with_active(key=new_key, data=old, info=old_info))

    def get_name_fragments(self):
        if self.new_key:
            return [f"copy_{self.new_key}={self.old_key}"]
        return [f"copy_{self.old_key}"]


_COPY_FORMAT = "new_key=old_key | old_key"


@arg_parser(
    dest="adaptors",
    flags="--copy",
    metavar=_COPY_FORMAT,
    help=f"Copy a variable and all its metadata.",
)
def parse_copy(arg: str) -> Copy:
    if "=" in arg:
        new_key, old_key = parse_util.parse_assignment(arg, _COPY_FORMAT)
    else:
        new_key, old_key = None, arg
    new_key = parse_util.parse_optional_identifier(new_key, "new_key")
    old_key = parse_util.parse_identifier(old_key, "old_key")
    return Copy(new_key, old_key)
