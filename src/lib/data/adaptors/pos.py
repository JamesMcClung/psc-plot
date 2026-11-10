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


def _get_mask[T: xr.DataArray | pd.Series](values: T, sel: slice, include_bounds: tuple[bool, bool]) -> T:
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
        var_keys_to_sel: dict[str | None, float | slice],
        var_keys_to_include_bounds: dict[str | None, tuple[bool, bool]] | None = None,
    ):
        """A `None` key stands for the active key."""
        self.var_keys_to_sel = var_keys_to_sel

        self.var_keys_to_include_bounds = var_keys_to_include_bounds or {}
        for key in self.var_keys_to_sel:
            self.var_keys_to_include_bounds.setdefault(key, (True, False))

    def _resolve_active_key(self, data: Field | List) -> tuple[dict[str, float | slice], dict[str, tuple[bool, bool]]]:
        if None not in self.var_keys_to_sel:
            return self.var_keys_to_sel, self.var_keys_to_include_bounds
        return (
            {key or data.require_active_key(): sel for key, sel in self.var_keys_to_sel.items()},
            {key or data.require_active_key(): bounds for key, bounds in self.var_keys_to_include_bounds.items()},
        )

    def apply_field(self, data: Field) -> Field:
        var_keys_to_sel, var_keys_to_include_bounds = self._resolve_active_key(data)
        active = data.require_active_subdata()
        var_keys_to_pos: dict[str, float] = {}
        var_keys_to_slice: dict[str, slice] = {}
        var_masks: list[xr.DataArray] = []
        for key, sel in var_keys_to_sel.items():
            if key in active.dims or key not in data.data:
                if isinstance(sel, float):
                    var_keys_to_pos[key] = sel
                else:
                    var_keys_to_slice[key] = sel
            elif isinstance(sel, slice):
                var_masks.append(_get_mask(data[key], sel, var_keys_to_include_bounds[key]))
            else:
                raise ValueError(f"--pos on field '{key}' needs a range (lower?:upper?), not a single value")

        for mask in var_masks:
            active = active.where(mask)
        return data.with_active(data=active.sel(var_keys_to_pos, method="nearest").sel(var_keys_to_slice))

    def apply_list(self, data: List) -> List:
        var_keys_to_sel, var_keys_to_include_bounds = self._resolve_active_key(data)
        coord_isels: dict[str, int | slice] = {}
        value_sels: dict[str, slice] = {}
        for key, sel in var_keys_to_sel.items():
            if key in data.coordss():
                coord_isels[key] = _sel_to_isel(data.coordss()[key], sel, var_keys_to_include_bounds[key])
            elif isinstance(sel, slice):
                value_sels[key] = sel
            else:
                raise ValueError(f"Data has no coordinate information for key {key}")

        if coord_isels:
            data = Idx(coord_isels).apply_list(data)

        if value_sels:
            df = data.data
            for key, sel in value_sels.items():
                df = df[_get_mask(df[key], sel, var_keys_to_include_bounds[key])]
            data = data.assign(df)

        return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(data_util.sel_to_frag(sel) if key is None else f"{key}={data_util.sel_to_frag(sel)}" for key, sel in self.var_keys_to_sel.items())
        return [f"pos_{subfrags}"]


POS_FORMAT = "[var_key=][pos | lower?:upper?]"


@arg_parser(
    dest="adaptors",
    flags="--pos",
    metavar=POS_FORMAT,
    help="select data nearest to the given position, or between the lower position (inclusive) and upper position (exclusive); if var_key points to a field, the active field is nan'd where the given field lies outside of the given range",
    nargs="+",
)
def parse_pos(args: list[str]) -> Pos:
    var_keys_to_sel: dict[str | None, float | slice] = {}
    for arg in args:
        if "=" in arg:
            [key, sel_arg] = parse_util.parse_assignment(arg, POS_FORMAT)
            parse_util.parse_identifier(key, "var_key")
        else:
            key, sel_arg = None, arg

        if ":" in sel_arg:
            var_keys_to_sel[key] = parse_util.parse_slice(sel_arg, float)
        else:
            var_keys_to_sel[key] = parse_util.parse_number(sel_arg, "pos", float)

    return Pos(var_keys_to_sel)
