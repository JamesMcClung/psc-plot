import pandas as pd
import xarray as xr

from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors import parse_util
from lib.data.adaptors.registry import adaptor_parser
from lib.data.keys import COORDS_KEY


class Idx(AtomicAdaptor):
    def __init__(self, dim_names_to_idx: dict[str, int]):
        self.dim_names_to_idx = dim_names_to_idx

    def apply_atomic[T: xr.DataArray | pd.DataFrame](self, data: T) -> T:
        if isinstance(data, xr.DataArray):
            return data.isel(self.dim_names_to_idx)
        elif isinstance(data, pd.DataFrame):
            coords = data.attrs[COORDS_KEY]
            new_coords = dict(coords)
            for dim, idx in self.dim_names_to_idx.items():
                if dim not in coords:
                    raise ValueError(f"Data has no coordinate information for dimension {dim}")

                pos = float(coords[dim][idx])
                data = data[data[dim] == pos]
                new_coords[dim] = pos

            data.attrs[COORDS_KEY] = new_coords
            return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={idx}" for dim_name, idx in self.dim_names_to_idx.items())
        return [f"idx_{subfrags}"]


IDX_FORMAT = "dim_name=idx"


@adaptor_parser(
    "--idx",
    metavar=IDX_FORMAT,
    help="select data at the given index",
    nargs="+",
)
def parse_idx(args: list[str]) -> Idx:
    dim_names_to_idx = {}
    for arg in args:
        split_arg = arg.split("=")

        if len(split_arg) != 2:
            parse_util.fail_format(arg, IDX_FORMAT)

        [dim_name, idx_arg] = split_arg

        parse_util.check_identifier(dim_name, "dim_name")
        idx = parse_util.parse_number(idx_arg, "idx", int)

        dim_names_to_idx[dim_name] = idx

    return Idx(dim_names_to_idx)
