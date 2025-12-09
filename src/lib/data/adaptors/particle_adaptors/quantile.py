import dask.dataframe as dd
import pandas as pd

from lib.data import data_util
from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors import parse_util
from lib.data.adaptors.field_adaptors.pos import Pos
from lib.data.adaptors.registry import adaptor_parser


class Quantile(AtomicAdaptor):
    def __init__(self, dim_names_to_quants: dict[str, slice]):
        self.dim_names_to_quants = dim_names_to_quants

    def apply_atomic[T: pd.DataFrame | dd.DataFrame](self, data: T) -> T:
        dim_names_to_slices: dict[str, slice] = {}

        for dim, quants in self.dim_names_to_quants.items():
            lower_quant_val = None
            upper_quant_val = None

            if quants.start not in [0.0, None]:
                lower_quant_val = data[dim].quantile(quants.start)

            if quants.stop not in [1.0, None]:
                upper_quant_val = data[dim].quantile(quants.stop)

            dim_names_to_slices[dim] = slice(lower_quant_val, upper_quant_val)

        dim_names_to_include_bounds = {dim: (True, True) for dim in dim_names_to_slices}

        return Pos(dim_names_to_slices, dim_names_to_include_bounds).apply_atomic(data)

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={data_util.sel_to_frag(quants)}" for dim_name, quants in self.dim_names_to_quants.items())
        return [f"quantile_{subfrags}"]


QUANTILE_FORMAT = "dim_name=lower?:upper?"


@adaptor_parser(
    "--quantile",
    metavar=QUANTILE_FORMAT,
    help="select data within the given quantiles (both bounds are inclusive), specified between 0 and 1",
    nargs="+",
)
def parse_quantile(args: list[str]) -> Quantile:
    dim_names_to_quants = {}
    for arg in args:
        [dim_name, sel_arg] = parse_util.parse_assignment(arg, QUANTILE_FORMAT)

        parse_util.check_identifier(dim_name, "dim_name")
        dim_names_to_quants[dim_name] = parse_util.parse_slice(sel_arg, float)

    return Quantile(dim_names_to_quants)
