import numpy as np
import pandas as pd
import xarray as xr

from lib.data import data_util
from lib.data.adaptor import MetadataAdaptor
from lib.data.adaptors.idx import Idx
from lib.data.data_with_attrs import Field, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def _sel_to_isel(coords: np.ndarray, sel: float | slice, include_bounds: tuple[bool, bool]) -> int | slice:
    """Translate a coordinate-value selection into an integer-index selection
    against the given coords. Used by Pos to delegate to Idx."""
    if isinstance(sel, float):
        return int(np.argmin(np.abs(coords - sel)))
    inc_lo, inc_hi = include_bounds
    start = None if sel.start is None else int(np.searchsorted(coords, sel.start, side="left" if inc_lo else "right"))
    stop = None if sel.stop is None else int(np.searchsorted(coords, sel.stop, side="right" if inc_hi else "left"))
    return slice(start, stop)


def _in_range[T: (xr.DataArray, pd.Series)](values: T, sel: slice, include_bounds: tuple[bool, bool]) -> T:
    """Whether each value lies within the selection's bounds."""
    inc_lo, inc_hi = include_bounds
    mask = values == values  # all true, except for nans
    if sel.start is not None:
        mask &= (values >= sel.start) if inc_lo else (values > sel.start)
    if sel.stop is not None:
        mask &= (values <= sel.stop) if inc_hi else (values < sel.stop)
    return mask


class Pos(MetadataAdaptor):
    def __init__(
        self,
        dim_names_to_sel: dict[str, float | slice],
        dim_names_to_include_bounds: dict[str, tuple[bool, bool]] | None = None,
    ):
        self.dim_names_to_sel = dim_names_to_sel

        self.dim_names_to_include_bounds = dim_names_to_include_bounds or {}
        for dim_name in self.dim_names_to_sel:
            self.dim_names_to_include_bounds.setdefault(dim_name, (True, False))

    def apply_field(self, data: Field) -> Field:
        active = data.require_active_subdata()
        dim_names_to_pos: dict[str, float] = {}
        dim_names_to_slice: dict[str, slice] = {}
        var_masks: list[xr.DataArray] = []
        for name, sel in self.dim_names_to_sel.items():
            if name in active.dims or name not in data.data:
                if isinstance(sel, float):
                    dim_names_to_pos[name] = sel
                else:
                    dim_names_to_slice[name] = sel
            elif isinstance(sel, slice):
                var_masks.append(_in_range(data[name], sel, self.dim_names_to_include_bounds[name]))
            else:
                raise ValueError(f"--pos on variable '{name}' needs a range (lower?:upper?), not a single value")

        for mask in var_masks:
            active = active.where(mask)
        return data.with_active(data=active.sel(dim_names_to_pos, method="nearest").sel(dim_names_to_slice))

    def apply_list(self, data: List) -> List:
        coord_isels: dict[str, int | slice] = {}
        value_sels: dict[str, slice] = {}
        for dim, sel in self.dim_names_to_sel.items():
            if dim in data.coordss():
                coord_isels[dim] = _sel_to_isel(data.coordss()[dim], sel, self.dim_names_to_include_bounds[dim])
            elif isinstance(sel, slice):
                value_sels[dim] = sel
            else:
                raise ValueError(f"Data has no coordinate information for dimension {dim}")

        if coord_isels:
            data = Idx(coord_isels).apply_list(data)

        if value_sels:
            df = data.data
            for dim, sel in value_sels.items():
                df = df[_in_range(df[dim], sel, self.dim_names_to_include_bounds[dim])]
            data = data.assign(df)

        return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={data_util.sel_to_frag(sel)}" for dim_name, sel in self.dim_names_to_sel.items())
        return [f"pos_{subfrags}"]


POS_FORMAT = "dim_name=[pos | lower?:upper?]"


@arg_parser(
    dest="adaptors",
    flags="--pos",
    metavar=POS_FORMAT,
    help="select data nearest to the given position, or between the lower position (inclusive) and upper position (exclusive); a variable name in place of dim_name keeps the rows (particles) or values (fields; others become nan) where that variable is in the range",
    nargs="+",
)
def parse_pos(args: list[str]) -> Pos:
    dim_names_to_sel = {}
    for arg in args:
        [dim_name, sel_arg] = parse_util.parse_assignment(arg, POS_FORMAT)

        parse_util.parse_identifier(dim_name, "dim_name")
        if ":" in sel_arg:
            dim_names_to_sel[dim_name] = parse_util.parse_slice(sel_arg, float)
        else:
            dim_names_to_sel[dim_name] = parse_util.parse_number(sel_arg, "pos", float)

    return Pos(dim_names_to_sel)
