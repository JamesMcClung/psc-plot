import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors import parse_util
from lib.data.adaptors.registry import adaptor_parser
from lib.data.keys import COORDS_KEY


class Pos(AtomicAdaptor):
    def __init__(self, dim_names_to_sel: dict[str, float | slice]):
        self.dim_names_to_sel = dim_names_to_sel

    def apply_atomic[T: xr.DataArray | pd.DataFrame | dd.DataFrame](self, data: T) -> T:
        if isinstance(data, xr.DataArray):
            dim_names_to_pos = {dim_name: pos for dim_name, pos in self.dim_names_to_sel.items() if isinstance(pos, float)}
            dim_names_to_slice = {dim_name: s for dim_name, s in self.dim_names_to_sel.items() if isinstance(s, slice)}
            return data.sel(dim_names_to_pos, method="nearest").sel(dim_names_to_slice)
        else:
            coordss = data.attrs[COORDS_KEY]
            new_coordss = dict(coordss)

            for dim, sel in self.dim_names_to_sel.items():
                if isinstance(sel, float):
                    if dim not in coordss:
                        raise ValueError(f"Data has no coordinate information for dimension {dim}")

                    nearest_coord = float(coordss[dim][0])
                    for coord in coordss[dim]:
                        if abs(coord - sel) < abs(nearest_coord - sel):
                            nearest_coord = float(coord)

                    data = data[data[dim] == nearest_coord]
                    new_coordss[dim] = nearest_coord
                else:
                    if sel.start is not None:
                        data = data[data[dim] >= sel.start]

                    if sel.stop is not None:
                        data = data[data[dim] < sel.stop]

                    if dim in coordss:
                        coords = coordss[dim]

                        lower_idx = None if sel.start is None else np.searchsorted(coords, sel.start, side="right") - 1
                        upper_idx = None if sel.stop is None else np.searchsorted(coords, sel.stop, side="right")

                        new_coordss[dim] = coords[lower_idx:upper_idx]

            data.attrs[COORDS_KEY] = new_coordss
            return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={pos}" for dim_name, pos in self.dim_names_to_sel.items())
        return [f"pos_{subfrags}"]


POS_FORMAT = "dim_name=[pos | lower?:upper?]"


@adaptor_parser(
    "--pos",
    metavar=POS_FORMAT,
    help="select data nearest to the given position, or between the lower position (inclusive) and upper position (exclusive)",
    nargs="+",
)
def parse_pos(args: list[str]) -> Pos:
    dim_names_to_sel = {}
    for arg in args:
        split_arg = arg.split("=")

        if len(split_arg) != 2:
            parse_util.fail_format(arg, POS_FORMAT)

        [dim_name, sel_arg] = split_arg

        parse_util.check_identifier(dim_name, "dim_name")
        if ":" in sel_arg:
            dim_names_to_sel[dim_name] = slice(*parse_util.parse_range(sel_arg, float))
        else:
            dim_names_to_sel[dim_name] = parse_util.parse_number(sel_arg, "pos", float)

    return Pos(dim_names_to_sel)
