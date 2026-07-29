import math
from abc import ABC, abstractmethod
from typing import Iterable, Literal

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.projections import PolarAxes
from matplotlib.text import Text

from lib.plotting import plt_util
from lib.plotting.labeler import TreeLabeler
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PolarMeshInfo, ScatterInfo
from lib.plotting.renderer2 import Renderer2

type AxesIdx = tuple[int, int]


def _flatten_idx(axes_idx: tuple[int, int], ncols: int) -> int:
    return ncols * (axes_idx[1] - 1) + axes_idx[0]


def _setup_axes(figure: Figure, plot_infos: list[PlotInfo]) -> dict[AxesIdx, tuple[Axes, list[PlotInfo]]]:
    idx_to_infos: dict[AxesIdx, list[PlotInfo]] = {}
    for info in plot_infos:
        idx_to_infos.setdefault(info.axes_index, []).append(info)

    ncols = max(idx[0] for idx in idx_to_infos)
    nrows = max(idx[1] for idx in idx_to_infos)

    ret: dict[AxesIdx, tuple[Axes, list[PlotInfo]]] = {}
    for idx, infos in idx_to_infos.items():
        projection = infos[0].projection
        for info in infos[1:]:
            if info.projection != projection:
                raise ValueError("incompatible plots (TODO: better error message)")
        ax = figure.add_subplot(nrows, ncols, _flatten_idx(idx, ncols), projection=projection)
        ret[idx] = (ax, infos)

    return ret


def _get_aspect(info: PlotInfo2D) -> Literal["auto", "equal"]:
    if info.dim_units[info.x_dim] != info.dim_units[info.y_dim]:
        return "auto"

    x_lo, x_hi = info.dim_bounds[info.x_dim]
    y_lo, y_hi = info.dim_bounds[info.y_dim]
    if None in [x_lo, x_hi, y_lo, y_hi]:
        return "auto"

    if math.isclose(x_hi - x_lo, y_hi - y_lo):
        return "equal"

    return "auto"


def _one_or_none[T](objs: Iterable[T]) -> T | None:
    one = None
    for obj in objs:
        if one is None:
            one = obj
        elif obj != one:
            return None
    return one


def find_widest_bounds(boundss: Iterable[tuple[float | None, float | None]]) -> tuple[float | None, float | None]:
    lowest_bound = None
    highest_bound = None

    for bounds in boundss:
        if lowest_bound is None:
            lowest_bound = bounds[0]
        elif bounds[0] is not None and lowest_bound > bounds[0]:
            lowest_bound = bounds[0]

        if highest_bound is None:
            highest_bound = bounds[1]
        elif bounds[1] is not None and highest_bound < bounds[1]:
            highest_bound = bounds[1]

    return (lowest_bound, highest_bound)


class UpdateText:
    def __init__(self, text: Text, plot_info: PlotInfo):
        self.text = text
        self.plot_info = plot_info

    def __call__(self, *_):
        self.text.set_text(self.plot_info.get_title())


class AxesManager(ABC):
    @abstractmethod
    def get_renderers(self) -> list[Renderer2]: ...

    @abstractmethod
    def setup(self): ...

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


class AxesManagerSingle[A: Axes, PI: PlotInfo](AxesManager):
    def __init__(self, ax: A, info: PI):
        self.ax = ax
        self.info = info

    def setup_title(self):
        self.labeler = TreeLabeler(self.ax.title.set_text, self.info)
        self.labeler.update()

    def get_renderers(self):
        return [self.labeler]


class AxesManagerSingle2D[PI2D: PlotInfo2D](AxesManagerSingle[Axes, PI2D]):
    def setup(self):
        self.setup_title()
        self.setup_labels()
        self.setup_data()
        self.setup_scales()
        self.setup_bounds()

    def setup_labels(self):
        self.ax.set_xlabel(self.info.get_dim_label(self.info.x_dim))
        self.ax.set_ylabel(self.info.get_dim_label(self.info.y_dim))

    def setup_scales(self):
        self.ax.set_xscale(self.info.dim_scales[self.info.x_dim].to_axis_scale())
        self.ax.set_yscale(self.info.dim_scales[self.info.y_dim].to_axis_scale())

    def setup_bounds(self):
        self.ax.set_xlim(*self.info.dim_bounds[self.info.x_dim])
        self.ax.set_ylim(*self.info.dim_bounds[self.info.y_dim])


class AxesManagerSingleLine(AxesManagerSingle2D[LineInfo]):
    def setup_data(self):
        [line] = self.ax.plot(self.info.x_data, self.info.y_data, linestyle=self.info.line_style, scalex=False, scaley=False)
        self.info._setter_callbacks["x_data"] = line.set_xdata
        self.info._setter_callbacks["y_data"] = line.set_ydata
        self.info._setter_callbacks["line_style"] = line.set_linestyle


class AxesManagerSingleImage(AxesManagerSingle2D[ImageInfo]):
    def setup_data(self):
        image = self.ax.imshow(
            self.info.data,
            origin="lower",
            extent=(*self.info.dim_bounds[self.info.x_dim], *self.info.dim_bounds[self.info.y_dim]),
            norm=self.info.dim_scales[self.info.color_dim].to_color_norm(),
            interpolation="nearest",
            aspect=_get_aspect(self.info),
        )
        self.info._setter_callbacks["data"] = image.set_data

        self.ax.figure.colorbar(image)
        data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)


class AxesManagerSingleScatter(AxesManagerSingle2D[ScatterInfo]):
    def setup_data(self):
        if self.info.color_dim:
            scatter = self.ax.scatter(
                self.info.xy_data[:, 0],
                self.info.xy_data[:, 1],
                c=self.info.color_data,
                norm=self.info.dim_scales[self.info.color_dim].to_color_norm(),
                s=1,
            )
            self.info._setter_callbacks["color_data"] = scatter.set_array

            self.ax.figure.colorbar(scatter, label=self.info.get_dim_label(self.info.color_dim))
            data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
            plt_util.update_cbar(scatter, data_min_override=data_lower, data_max_override=data_upper)
        else:
            scatter = self.ax.scatter(
                self.info.xy_data[:, 0],
                self.info.xy_data[:, 1],
                color=self.ax._get_lines.get_next_color(),
                s=0.5,
            )
        self.ax.set_aspect(_get_aspect(self.info))

        update_data = lambda _=None: scatter.set_offsets(self.info.xy_data)
        self.info._setter_callbacks["xy_data"] = update_data


class AxesManagerSinglePolarMesh(AxesManagerSingle[PolarAxes, PolarMeshInfo]):
    def setup(self):
        self.setup_title()
        self.setup_labels()
        self.setup_scales()
        self.setup_data()

    def setup_labels(self):
        # FIXME make the labels work
        pass

    def setup_bounds(self):
        pass

    def setup_scales(self):
        self.ax.set_rscale(self.info.dim_scales[self.info.r_dim].to_axis_scale())

    def setup_data(self):
        image = self.ax.pcolormesh(
            *np.meshgrid(self.info.theta_vertices, self.info.r_vertices),
            self.info.data,
            shading="flat",
            norm=self.info.dim_scales[self.info.color_dim].to_color_norm(),
        )
        self.info._setter_callbacks["data"] = image.set_array

        self.ax.figure.colorbar(image)
        data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)


class AxesManagerMultiLine(AxesManager):
    def __init__(self, ax: Axes, infos: list[LineInfo]):
        self.ax = ax
        self.infos = infos
        self.lines: list[Line2D] = []  # populated later

    def get_renderers(self):
        return [self.labeler]

    def setup(self):
        self.setup_labels()
        self.setup_data()
        self.setup_title()  # after data, to make sure lines is populated
        self.setup_scales()
        self.setup_bounds()

    def setup_title(self):
        self.labeler = TreeLabeler(self.ax.title.set_text)
        for info, line in zip(self.infos, self.lines):
            line_labeler = TreeLabeler(line.set_label, info)
            self.labeler.add_child(line_labeler)
        self.labeler.update()
        self.ax.legend()

    def setup_labels(self):
        x_labels = [info.get_dim_label(info.x_dim) for info in self.infos]
        if (x_label := _one_or_none(x_labels)) is not None:
            self.ax.set_xlabel(x_label)
        else:
            raise NotImplementedError(f"x labels must all be the same, but found {x_labels}")

        y_labels = [info.get_dim_label(info.y_dim) for info in self.infos]
        y_units = [info.dim_units[info.y_dim] for info in self.infos]
        if (y_label := _one_or_none(y_labels)) is not None:
            self.ax.set_ylabel(y_label)
        elif (y_unit := _one_or_none(y_units)) is not None:
            self.ax.set_ylabel(y_unit.maybe_with_dollars())
        else:
            raise NotImplementedError(f"y labels must all be the same unit, but found {y_units}")

    def setup_scales(self):
        x_scales = [info.dim_scales[info.x_dim] for info in self.infos]
        if (x_scale := _one_or_none(x_scales)) is not None:
            self.ax.set_xscale(x_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"x scales must all be the same, but found {x_scales}")

        y_scales = [info.dim_scales[info.y_dim] for info in self.infos]
        if (y_scale := _one_or_none(y_scales)) is not None:
            self.ax.set_yscale(y_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"y scales must all be the same, but found {y_scales}")

    def setup_bounds(self):
        self.ax.set_xbound(*find_widest_bounds(info.dim_bounds[info.x_dim] for info in self.infos))
        self.ax.set_ybound(*find_widest_bounds(info.dim_bounds[info.y_dim] for info in self.infos))

    def setup_data(self):
        for info in self.infos:
            [line] = self.ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
            info._setter_callbacks["x_data"] = line.set_xdata
            info._setter_callbacks["y_data"] = line.set_ydata
            info._setter_callbacks["line_style"] = line.set_linestyle
            self.lines.append(line)


class AxesManagerImageAndLines(AxesManager):
    def __init__(self, ax: Axes, image_info: ImageInfo, line_infos: list[LineInfo]):
        self.image_ax = ax
        self.line_ax = ax.twinx()
        self.image_info = image_info
        self.line_infos = line_infos
        self.infos: list[PlotInfo2D] = [image_info, *line_infos]
        self.lines: list[Line2D] = []  # populated later

    def get_renderers(self):
        return [self.labeler]

    def setup(self):
        self.setup_labels()
        self.setup_data()
        self.setup_title()  # after data to get line info and cbar
        self.setup_scales()
        self.setup_bounds()

    def setup_title(self):
        self.labeler = TreeLabeler(self.image_ax.title.set_text)

        self.labeler.add_child(TreeLabeler(self.cbar.set_label, self.image_info))
        for info, line in zip(self.line_infos, self.lines):
            self.labeler.add_child(TreeLabeler(line.set_label, info))

        self.labeler.update()
        self.line_ax.legend()

    def setup_labels(self):
        x_labels = [info.get_dim_label(info.x_dim) for info in self.infos]
        if (x_label := _one_or_none(x_labels)) is not None:
            self.image_ax.set_xlabel(x_label)
        else:
            raise NotImplementedError(f"x labels must all be the same, but found {x_labels}")

        self.image_ax.set_ylabel(self.image_info.get_dim_label(self.image_info.y_dim))

        y_labels = [info.get_dim_label(info.y_dim) for info in self.line_infos]
        y_units = [info.dim_units[info.y_dim] for info in self.line_infos]
        if (y_label := _one_or_none(y_labels)) is not None:
            self.line_ax.set_ylabel(y_label)
        elif (y_unit := _one_or_none(y_units)) is not None:
            self.line_ax.set_ylabel(y_unit.maybe_with_dollars())
        else:
            raise NotImplementedError(f"line y labels must all be the same unit, but found {y_units}")

    def setup_scales(self):
        x_scales = [info.dim_scales[info.x_dim] for info in self.infos]
        if (x_scale := _one_or_none(x_scales)) is not None:
            self.image_ax.set_xscale(x_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"x scales must all be the same, but found {x_scales}")

        self.image_ax.set_yscale(self.image_info.dim_scales[self.image_info.y_dim].to_axis_scale())

        y_scales = [info.dim_scales[info.y_dim] for info in self.line_infos]
        if (y_scale := _one_or_none(y_scales)) is not None:
            self.line_ax.set_yscale(y_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"y scales must all be the same, but found {y_scales}")

    def setup_bounds(self):
        self.image_ax.set_xlim(*find_widest_bounds(info.dim_bounds[info.x_dim] for info in self.infos))
        self.image_ax.set_ylim(*self.image_info.dim_bounds[self.image_info.y_dim])
        self.line_ax.set_ylim(*find_widest_bounds(info.dim_bounds[info.y_dim] for info in self.line_infos))

    def setup_data(self):
        image = self.image_ax.imshow(
            self.image_info.data,
            origin="lower",
            extent=(*self.image_info.dim_bounds[self.image_info.x_dim], *self.image_info.dim_bounds[self.image_info.y_dim]),
            norm=self.image_info.dim_scales[self.image_info.color_dim].to_color_norm(),
            interpolation="nearest",
            aspect=_get_aspect(self.image_info),
        )
        self.image_info._setter_callbacks["data"] = image.set_data

        self.cbar = self.image_ax.figure.colorbar(image)
        data_lower, data_upper = self.image_info.dim_bounds[self.image_info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

        for info in self.line_infos:
            [line] = self.line_ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
            info._setter_callbacks["x_data"] = line.set_xdata
            info._setter_callbacks["y_data"] = line.set_ydata
            info._setter_callbacks["line_style"] = line.set_linestyle
            self.lines.append(line)


def setup_fig(plot_infos: list[PlotInfo]) -> tuple[Figure, list[Renderer2]]:
    figure = plt.figure(layout="constrained")
    renderers = []

    for ax, infos in _setup_axes(figure, plot_infos).values():
        manager: AxesManager
        if len(infos) == 1:
            info = infos[0]
            if isinstance(info, LineInfo):
                manager = AxesManagerSingleLine(ax, info)
            elif isinstance(info, ImageInfo):
                manager = AxesManagerSingleImage(ax, info)
            elif isinstance(info, ScatterInfo):
                manager = AxesManagerSingleScatter(ax, info)
            elif isinstance(info, PolarMeshInfo):
                manager = AxesManagerSinglePolarMesh(ax, info)
            else:
                raise TypeError(f"unknown type: {infos.__class__!r}")
        else:
            image_infos = [info for info in infos if isinstance(info, ImageInfo)]
            line_infos = [info for info in infos if isinstance(info, LineInfo)]
            if not image_infos:
                manager = AxesManagerMultiLine(ax, line_infos)
            elif len(image_infos) == 1:
                manager = AxesManagerImageAndLines(ax, image_infos[0], line_infos)
            else:
                raise NotImplementedError("don't yet support multiple non-line plots per axes")

        manager.setup()
        renderers += manager.get_renderers()

    return figure, renderers
