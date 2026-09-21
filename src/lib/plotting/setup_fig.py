from typing import Iterable

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes

from lib.plotting import plt_util
from lib.plotting.data_setter import DataSetter
from lib.plotting.grid import Grid
from lib.plotting.labeler import UnitLabeler
from lib.plotting.panel import Panel
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PlotInfoColor, PlotInfoMaybeColor, PolarMeshInfo, ScatterInfo


def setup_colorbar(ax: Axes, target: ScalarMappable, info: PlotInfoColor | PlotInfoMaybeColor) -> Colorbar:
    assert info.color_dim
    cbar = ax.figure.colorbar(target)
    # TODO work into everything
    data_lower, data_upper = info.dim_bounds[info.color_dim]
    plt_util.update_cbar(target, data_min_override=data_lower, data_max_override=data_upper)
    return cbar


def setup_data_setter(panel: Panel, ax: Axes, info: PlotInfo):
    setter = DataSetter.dispatch_init(ax, info)
    panel.wire_data_setter(setter)
    if info.has_legend():
        panel.wire_legend_label(setter.artist, info)
    if info.has_colorbar():
        cbar = setup_colorbar(ax, setter.artist, info)
        panel.wire_cbar_label(cbar, info)
    if isinstance(info, PlotInfo2D):
        ax.set_aspect(info.get_aspect())
    return setter


def setup_panel_xy(ax: Axes, infos: list[PlotInfo2D]) -> Panel:
    panel = Panel()
    panel.wire_title(ax.title)

    for info in infos:
        if not panel.try_wire_unit_labeler_xy(ax, "x", info):
            raise Exception(f"the x-axis of {info} is incompatible with at least one other plot")
        panel.wire_bounds_setter_xy(ax, "x", info)
        panel.wire_scale(ax, "x", info)

    # Choose whether each info uses the left y-axis or the right y-axis, preferring left.
    # Only legend-supporting data (e.g. lines, but not images) are allowed on the right.
    left_ax = ax
    right_ax: Axes | None = None

    left_y_axis_only_infos = [info for info in infos if not info.has_legend()]
    for info in left_y_axis_only_infos:
        if panel.try_wire_unit_labeler_xy(left_ax, "y", info):
            panel.wire_bounds_setter_xy(left_ax, "y", info)
            panel.wire_scale(left_ax, "y", info)
            setup_data_setter(panel, left_ax, info)
            continue

        raise Exception(f"{info} must use the left y-axis, but is incompatible with at least one other left-y-axis-only plot")

    either_y_axis_infos = [info for info in infos if info.has_legend()]
    for info in either_y_axis_infos:
        if panel.try_wire_unit_labeler_xy(left_ax, "y", info):
            panel.wire_bounds_setter_xy(left_ax, "y", info)
            panel.wire_scale(left_ax, "y", info)
            setup_data_setter(panel, left_ax, info)
            continue

        if not right_ax:
            right_ax = left_ax.twinx()

        if panel.try_wire_unit_labeler_xy(right_ax, "y", info):
            panel.wire_bounds_setter_xy(right_ax, "y", info)
            panel.wire_scale(right_ax, "y", info)
            setup_data_setter(panel, right_ax, info)
            continue

        raise Exception(f"the y-axis of {info} and least two other plots are mutually incompatible")

    return panel


def setup_panel_polar(ax: PolarAxes, infos: list[PolarMeshInfo]) -> Panel:
    polar_mesh_infos = infos

    panel = Panel()
    panel.wire_title(ax.title)

    if len(polar_mesh_infos) > 1:
        raise NotImplementedError("don't yet support overplotting polar meshes")

    [info] = polar_mesh_infos

    panel.wire_scale(ax, "r", info)
    setup_data_setter(panel, ax, info)

    return panel


def setup_panel(ax: Axes, infos: list[PlotInfo]) -> Panel:
    infos_2d = [info for info in infos if isinstance(info, PlotInfo2D)]
    infos_polar = [info for info in infos if isinstance(info, PolarMeshInfo)]

    if infos_2d and infos_polar:
        raise Exception("can't overplot Cartesian and polar data")

    if infos_2d:
        return setup_panel_xy(ax, infos)
    if infos_polar:
        assert isinstance(ax, PolarAxes)
        return setup_panel_polar(ax, infos)


def setup_fig(plot_infos: list[PlotInfo]) -> tuple[Figure, Grid]:
    figure = plt.figure(layout="constrained")

    grid = Grid(figure, plot_infos)
    for loc, infos in grid.infos.items():
        ax = grid.setup_ax(loc)
        panel = setup_panel(ax, infos)
        grid.set_panel(loc, panel)

    grid.update_labels()
    grid.update_bounds()

    return figure, grid
