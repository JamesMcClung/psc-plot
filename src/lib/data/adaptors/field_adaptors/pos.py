import pandas as pd
import xarray as xr

from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors import parse_util
from lib.data.adaptors.registry import adaptor_parser
from lib.data.keys import COORDS_KEY


class Pos(AtomicAdaptor):
    def __init__(self, dim_names_to_pos: dict[str, int]):
        self.dim_names_to_pos = dim_names_to_pos

    def apply_atomic[T: xr.DataArray | pd.DataFrame](self, data: T) -> T:
        if isinstance(data, xr.DataArray):
            return data.sel(self.dim_names_to_pos, method="nearest")
        elif isinstance(data, pd.DataFrame):
            coords = data.attrs[COORDS_KEY]
            new_coords = dict(coords)
            for dim, pos in self.dim_names_to_pos.items():
                if dim not in coords:
                    raise ValueError(f"Data has no coordinate information for dimension {dim}")

                nearest_coord = float(coords[dim][0])
                for coord in coords[dim]:
                    if abs(coord - pos) < abs(nearest_coord - pos):
                        nearest_coord = float(coord)

                data = data[data[dim] == nearest_coord]
                new_coords[dim] = nearest_coord

            data.attrs[COORDS_KEY] = new_coords
            return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={pos}" for dim_name, pos in self.dim_names_to_pos.items())
        return [f"pos_{subfrags}"]


POS_FORMAT = "dim_name=pos"


@adaptor_parser(
    "--pos",
    metavar=POS_FORMAT,
    help="select data nearest to the given position",
    nargs="+",
)
def parse_pos(args: list[str]) -> Pos:
    dim_names_to_pos = {}
    for arg in args:
        split_arg = arg.split("=")

        if len(split_arg) != 2:
            parse_util.fail_format(arg, POS_FORMAT)

        [dim_name, pos_arg] = split_arg

        parse_util.check_identifier(dim_name, "dim_name")
        pos = parse_util.parse_number(pos_arg, "pos", float)

        dim_names_to_pos[dim_name] = pos

    return Pos(dim_names_to_pos)
