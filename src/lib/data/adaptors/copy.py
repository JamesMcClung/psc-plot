from lib.data.adaptor import WorldAdaptor
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Copy(WorldAdaptor):
    def __init__(self, new_key: str, old_key: str):
        self.new_key = new_key
        self.old_key = old_key

    def apply_world(self, world):
        active = world.require_active_data()
        old = active[self.old_key]
        old_info = active.metadata.var_infos[self.old_key]
        return world.with_active(data=active.with_active(key=self.new_key, data=old, info=old_info))

    def get_name_fragments(self):
        return [f"copy_{self.new_key}={self.old_key}"]


_COPY_FORMAT = "new_key=old_key"


@arg_parser(
    dest="adaptors",
    flags="--copy",
    metavar=_COPY_FORMAT,
    help=f"Copy a variable and all its metadata.",
)
def parse_copy(arg: str) -> Copy:
    new_key, old_key = parse_util.parse_assignment(arg, _COPY_FORMAT)
    new_key = parse_util.parse_identifier(new_key, "new_key")
    old_key = parse_util.parse_identifier(old_key, "old_key")
    return Copy(new_key, old_key)
