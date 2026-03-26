import dask.dataframe as dd

from lib.data.adaptor import CheckedAdaptor
from lib.data.data_with_attrs import List
from lib.derived_particle_variables.derived_particle_variable import (
    derive_particle_variable,
)
from lib.parsing.args_registry import arg_parser


class Derive(CheckedAdaptor):
    def __init__(self, var_key: str):
        self.var_key = var_key

    def apply_checked(self, data: List) -> dd.DataFrame:
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
    return Derive(var_key)
