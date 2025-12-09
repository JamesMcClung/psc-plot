import pandas as pd
import xarray as xr

from lib.data import data_util
from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors import parse_util
from lib.data.adaptors.registry import adaptor_parser
from lib.data.keys import COORDS_KEY


class Idx(AtomicAdaptor):
    def __init__(self, dim_names_to_isel: dict[str, int | slice]):
        self.dim_names_to_isel = dim_names_to_isel

    def apply_atomic[T: xr.DataArray | pd.DataFrame](self, data: T) -> T:
        if isinstance(data, xr.DataArray):
            return data.isel(self.dim_names_to_isel)
        elif isinstance(data, pd.DataFrame):
            coords = data.attrs[COORDS_KEY]
            new_coords = dict(coords)
            for dim, isel in self.dim_names_to_isel.items():
                if dim not in coords:
                    raise ValueError(f"Data has no coordinate information for dimension {dim}")

                if isinstance(isel, int):
                    pos = float(coords[dim][isel])
                    data = data[data[dim] == pos]
                    new_coords[dim] = pos
                else:
                    if isel.start not in [None, 0]:
                        pos_lower = float(coords[dim][isel.start])
                        data = data[data[dim] >= pos_lower]

                    if isel.stop is not None:
                        pos_upper = float(coords[dim][isel.stop])
                        data = data[data[dim] < pos_upper]

                    new_coords[dim] = coords[dim][isel]

            data.attrs[COORDS_KEY] = new_coords
            return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={data_util.sel_to_frag(isel)}" for dim_name, isel in self.dim_names_to_isel.items())
        return [f"idx_{subfrags}"]


IDX_FORMAT = "dim_name=[idx | lower?:upper?]"


@adaptor_parser(
    "--idx",
    metavar=IDX_FORMAT,
    help="select data at the given index, or between the lower index (inclusive) and upper index (exclusive)",
    nargs="+",
)
def parse_idx(args: list[str]) -> Idx:
    dim_names_to_isel = {}
    for arg in args:
        split_arg = arg.split("=")

        if len(split_arg) != 2:
            parse_util.fail_format(arg, IDX_FORMAT)

        [dim_name, isel_arg] = split_arg

        parse_util.check_identifier(dim_name, "dim_name")
        if ":" in isel_arg:
            dim_names_to_isel[dim_name] = parse_util.parse_slice(isel_arg, int)
        else:
            dim_names_to_isel[dim_name] = parse_util.parse_number(isel_arg, "idx", int)

    return Idx(dim_names_to_isel)
