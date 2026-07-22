from typing import Literal

import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes

from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting.hook import Hook
from lib.plotting.plot_info import PlotInfo2D

type DimName = str
type MajorGridlineSpacing = float | None
type MinorNLines = int | None
type MajorGridParams = dict[DimName, MajorGridlineSpacing]
type MinorGridParams = dict[DimName, MinorNLines]


def set_grid(axes: Axes, grid_type: Literal["major", "minor"], axis_id: Literal["x", "y"], tick_coords: npt.ArrayLike | None):
    set_ticks = {"x": axes.set_xticks, "y": axes.set_yticks}[axis_id]
    minor = grid_type == "minor"
    color = "lightgray" if minor else "darkgray"

    if tick_coords is not None:
        set_ticks(tick_coords, minor=minor)
    axes.grid(axis=axis_id, which=grid_type, color=color)


def get_tick_coords(lower_bound: float, upper_bound: float, spacing: float) -> np.ndarray:
    return np.arange(lower_bound, upper_bound, spacing)


class Grid(Hook):
    def __init__(self, major: MajorGridParams, minor: MinorGridParams):
        self.major = major
        self.minor = minor

    def post_init_fig(self, message):
        # Ensure major lines are enabled when minor lines are present
        for dim_name in self.minor:
            self.major.setdefault(dim_name, None)

        assert isinstance(message.plot_info, PlotInfo2D)

        # Draw major lines with the given spacing
        for dim_name, gridline_spacing in self.major.items():
            axis_id = get_axis_id(message.plot_info, dim_name)

            if gridline_spacing is None:
                tick_coords = None
            else:
                tick_coords = get_tick_coords(*message.plot_info.dim_bounds[dim_name], gridline_spacing)

            set_grid(message.axes, "major", axis_id, tick_coords)

        # Draw the given number of minor lines between major lines
        for dim_name, nlines in self.minor.items():
            axis_id = get_axis_id(message.plot_info, dim_name)

            if nlines is None:
                tick_coords = None
            else:
                get_ticks = {"x": message.axes.get_xticks, "y": message.axes.get_yticks}[axis_id]
                major_tick_coords = np.concat([get_ticks(minor=False), [message.plot_info.dim_bounds[dim_name][1]]])
                tick_coords = np.concat([np.linspace(left, right, nlines + 1, endpoint=False)[1:] for left, right in zip(major_tick_coords[:-1], major_tick_coords[1:])])

            set_grid(message.axes, "minor", axis_id, tick_coords)


def get_axis_id(info: PlotInfo2D, dim_name: str) -> Literal["x", "y"]:
    id_map = {info.x_dim: "x", info.y_dim: "y"}
    if dim_name not in id_map:
        message = f"Dimension '{dim_name}' isn't being shown on an axis. Axis dimensions are: {id_map.keys()}"
        raise ValueError(message)

    return id_map[dim_name]


MAJOR_MARKER = "major"
MINOR_MARKER = "minor"
MAJOR_SPACING_NAME = "spacing"
MINOR_NLINES_NAME = "nlines"
MAJOR_ITEM_FORMAT = f"dim_name[={MAJOR_SPACING_NAME}]"
MINOR_ITEM_FORMAT = f"dim_name[={MINOR_NLINES_NAME}]"
GRID_FORMAT = (
    f"[{MAJOR_ITEM_FORMAT} ...]",
    f"{MAJOR_MARKER} [{MAJOR_ITEM_FORMAT} ...] | {MINOR_MARKER} [{MINOR_ITEM_FORMAT} ...]",
)


@arg_parser(
    dest="hooks",
    flags="--grid",
    metavar=GRID_FORMAT,
    nargs="+",
    help="Mark the given axes with major and/or minor gridlines. The spacing between major grid lines can be specified, as can the number of minor lines between major lines. If unspecified, major/minor lines are placed at preexisting major/minor tick locations. Note that linear axes have no minor ticks by default.",
)
def parse_grid(args: list[str]) -> Grid:
    major: MajorGridParams = {}
    minor: MajorGridParams = {}

    current_grid_type = MAJOR_MARKER

    for arg in args:
        if arg in [MAJOR_MARKER, MINOR_MARKER]:
            current_grid_type = arg
        else:
            if current_grid_type == MAJOR_MARKER:
                dim_name, spacing_arg = parse_util.parse_optional_assignment(arg, MAJOR_ITEM_FORMAT)
                grid_spacing = parse_util.parse_optional_number(spacing_arg, MAJOR_SPACING_NAME, float)

                major[dim_name] = grid_spacing
            elif current_grid_type == MINOR_MARKER:
                dim_name, nlines_arg = parse_util.parse_optional_assignment(arg, MINOR_ITEM_FORMAT)
                nlines = parse_util.parse_optional_number(nlines_arg, MINOR_NLINES_NAME, int)

                minor[dim_name] = nlines

    return Grid(major, minor)
