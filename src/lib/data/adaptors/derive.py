from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import List
from lib.derived_particle_variables.derived_particle_variable import (
    DERIVED_PARTICLE_VARIABLES,
    derive_particle_variable,
)
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Derive(MetadataAdaptor):
    def __init__(self, var_key: str):
        self.var_key = var_key

    def apply_list(self, data: List) -> List:
        return derive_particle_variable(data, self.var_key, "prt")


_DERIVE_FORMAT = "var_key"


@arg_parser(
    dest="adaptors",
    flags="--derive",
    metavar=_DERIVE_FORMAT,
    help="derive the given variable from existing variables",
)
def parse_derive(arg: str) -> Derive:
    var_key = arg
    parse_util.check_value(var_key, "var_key", DERIVED_PARTICLE_VARIABLES["prt"])
    return Derive(var_key)
