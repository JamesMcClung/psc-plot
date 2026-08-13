from abc import abstractmethod
from dataclasses import dataclass, field

from lib.config import _DATA_DIR_KEY
from lib.data.adaptor import WorldAdaptor
from lib.data.data_world import DataWorld
from lib.data.ensure_derived import ensure_derived
from lib.data.loader import load
from lib.data.types import SubdataKey
from lib.file_util import Prepath
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


@dataclass
class With(WorldAdaptor):
    include_with_in_name_fragment: bool = field(init=False, default=True)

    @abstractmethod
    def get_prepath_and_key(self, world: DataWorld) -> tuple[Prepath | None, SubdataKey | None]: ...

    def apply_world(self, world):
        prepath, key = self.get_prepath_and_key(world)
        if not prepath:
            data = world.require_active_data()
        elif prepath in world.datas:
            data = world.datas[prepath]
        else:
            data = load(world.config, prepath)

        if key:
            data = ensure_derived(data, key)
        data = data.with_active(key=key)

        return world.with_active(prepath=prepath, data=data)

    @abstractmethod
    def get_name_subfragment(self) -> str: ...

    def get_name_fragments(self) -> list[str]:
        maybe_with = "with_" if self.include_with_in_name_fragment else ""
        return [maybe_with + self.get_name_subfragment()]


@dataclass
class With2(With):
    prepath: Prepath | None
    key: SubdataKey | None

    def get_prepath_and_key(self, world):
        return self.prepath, self.key

    def get_name_subfragment(self):
        maybe_prepath = self.prepath + SCOPE_OP if self.prepath else ""
        maybe_key = self.key or ""
        return maybe_prepath + maybe_key


@dataclass
class With1(With):
    prepath_or_key: Prepath | SubdataKey

    def get_prepath_and_key(self, world):
        if (data := world.active_data) is not None and self.prepath_or_key in data:
            return None, self.prepath_or_key
        return self.prepath_or_key, None

    def get_name_subfragment(self):
        return self.prepath_or_key


SCOPE_OP = "::"
WITH_FORMAT = f"prepath{SCOPE_OP}var_key | var_key | prepath"


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
        key = parse_util.parse_optional_identifier(key_arg, "key")
        return With2(prepath, key)
    elif len(split_arg) == 1:
        [prepath_or_key] = split_arg
        return With1(prepath_or_key)
    else:
        parse_util.fail_format(arg, WITH_FORMAT)


def parse_initial_with(arg: str) -> With:
    with_ = parse_with(arg)
    with_.include_with_in_name_fragment = False
    return with_
