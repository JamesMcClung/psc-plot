from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes

from lib.plotting import plt_util
from lib.plotting.axis_id import AxisId
from lib.plotting.data_setter import DataSetter
from lib.plotting.grid import Grid
from lib.plotting.labeler import UnitLabeler
from lib.plotting.panel import Panel
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PlotInfoColor, PlotInfoMaybeColor, PolarMeshInfo, ScatterInfo


def _one_or_none[T](objs: Iterable[T]) -> T | None:
    one = None
    for obj in objs:
        if one is None:
            one = obj
        elif obj != one:
            return None
    return one


def setup_colorbar(ax: Axes, target: ScalarMappable, info: PlotInfoColor | PlotInfoMaybeColor) -> Colorbar:
    assert info.color_dim
    cbar = ax.figure.colorbar(target)
    # TODO work into everything
    data_lower, data_upper = info.dim_bounds[info.color_dim]
    plt_util.update_cbar(target, data_min_override=data_lower, data_max_override=data_upper)
    return cbar


@dataclass
class AxesManager(ABC):
    panel: Panel = field(init=False, default_factory=Panel)

    @abstractmethod
    def setup(self) -> Panel: ...

    @abstractmethod
    def setup_title(self): ...

    @abstractmethod
    def setup_labels(self): ...

    @abstractmethod
    def setup_scales(self): ...

    @abstractmethod
    def setup_bounds(self): ...

    @abstractmethod
    def setup_data(self): ...


def set_scales_xy(ax: Axes, axis_id: AxisId, infos: list[PlotInfo2D]):
    match axis_id:
        case "x":
            scales = [info.dim_scales[info.x_dim] for info in infos]
            set_scale = ax.set_xscale
        case "y":
            scales = [info.dim_scales[info.y_dim] for info in infos]
            set_scale = ax.set_yscale
    if (scale := _one_or_none(scales)) is not None:
        set_scale(scale.to_axis_scale())
    else:
        raise NotImplementedError(f"{axis_id} scales must all be the same, but found {scales}")


def set_scales_rtheta(ax: PolarAxes, infos: list[PolarMeshInfo]):
    r_scales = [info.dim_scales[info.r_dim] for info in infos]
    if (r_scale := _one_or_none(r_scales)) is not None:
        ax.set_rscale(r_scale.to_axis_scale())
    else:
        raise NotImplementedError(f"r scales must all be the same, but found {r_scales}")


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

    set_scales_xy(ax, "x", infos)
    panel.wire_bounds_setter_xy(ax, "x", infos)
    for info in infos:
        if not panel.try_wire_unit_labeler_xy(ax, "x", info):
            raise Exception(f"the x-axis of {info} is incompatible with at least one other plot")

    # Choose whether each info uses the left y-axis or the right y-axis, preferring left.
    # Only legend-supporting data (e.g. lines, but not images) are allowed on the right.
    left_infos: list[PlotInfo] = []
    right_infos: list[PlotInfo] = []

    left_ax = ax
    right_ax: Axes | None = None

    left_y_axis_only_infos = [info for info in infos if not info.has_legend()]
    for info in left_y_axis_only_infos:
        if panel.try_wire_unit_labeler_xy(left_ax, "y", info):
            left_infos.append(info)
            continue

        raise Exception(f"{info} must use the left y-axis, but is incompatible with at least one other left-y-axis-only plot")

    either_y_axis_infos = [info for info in infos if info.has_legend()]
    for info in either_y_axis_infos:
        if panel.try_wire_unit_labeler_xy(left_ax, "y", info):
            left_infos.append(info)
            continue

        if not right_ax:
            right_ax = left_ax.twinx()

        if panel.try_wire_unit_labeler_xy(right_ax, "y", info):
            right_infos.append(info)
            continue

        raise Exception(f"the y-axis of {info} and least two other plots are mutually incompatible")

    if right_infos:
        set_scales_xy(right_ax, "y", right_infos)
        panel.wire_bounds_setter_xy(right_ax, "y", right_infos)

        for info in right_infos:
            setup_data_setter(panel, right_ax, info)

    if left_infos:
        set_scales_xy(left_ax, "y", left_infos)
        panel.wire_bounds_setter_xy(left_ax, "y", left_infos)

        for info in left_infos:
            setup_data_setter(panel, left_ax, info)

    return panel


def setup_panel_polar(ax: PolarAxes, infos: list[PolarMeshInfo]) -> Panel:
    polar_mesh_infos = infos

    panel = Panel()
    panel.wire_title(ax.title)

    if len(polar_mesh_infos) > 1:
        raise NotImplementedError("don't yet support overplotting polar meshes")

    [info] = polar_mesh_infos

    set_scales_rtheta(ax, infos)
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
