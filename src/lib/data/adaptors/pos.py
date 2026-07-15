import numpy as np

from lib.data import data_util
from lib.data.adaptor import MetadataAdaptor
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
        dim_names_to_pos = {dim_name: pos for dim_name, pos in self.dim_names_to_sel.items() if isinstance(pos, float)}
        dim_names_to_slice = {dim_name: s for dim_name, s in self.dim_names_to_sel.items() if isinstance(s, slice)}
        return data.assign_data(data.data.sel(dim_names_to_pos, method="nearest").sel(dim_names_to_slice))

    def apply_list(self, data: List) -> List:
        # Lazy-import Idx to avoid a circular import via lib.plotting.animated_plot.
        from lib.data.adaptors.idx import Idx

        coord_isels: dict[str, int | slice] = {}
        value_sels: dict[str, slice] = {}
        for dim, sel in self.dim_names_to_sel.items():
            if dim in data.coordss:
                coord_isels[dim] = _sel_to_isel(data.coordss[dim], sel, self.dim_names_to_include_bounds[dim])
            elif isinstance(sel, slice):
                value_sels[dim] = sel
            else:
                raise ValueError(f"Data has no coordinate information for dimension {dim}")

        if coord_isels:
            data = Idx(coord_isels).apply_list(data)

        if value_sels:
            df = data.data
            for dim, sel in value_sels.items():
                inc_lo, inc_hi = self.dim_names_to_include_bounds[dim]
                if sel.start is not None:
                    df = df[df[dim] >= sel.start] if inc_lo else df[df[dim] > sel.start]
                if sel.stop is not None:
                    df = df[df[dim] <= sel.stop] if inc_hi else df[df[dim] < sel.stop]
            data = data.assign_data(df)

        return data

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={data_util.sel_to_frag(sel)}" for dim_name, sel in self.dim_names_to_sel.items())
        return [f"pos_{subfrags}"]


POS_FORMAT = "dim_name=[pos | lower?:upper?]"


@arg_parser(
    dest="adaptors",
    flags="--pos",
    metavar=POS_FORMAT,
    help="select data nearest to the given position, or between the lower position (inclusive) and upper position (exclusive)",
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
