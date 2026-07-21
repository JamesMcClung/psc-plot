from abc import ABC, abstractmethod
from typing import Any, Iterable, overload

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes
from matplotlib.text import Text

from lib.plotting import plt_util
from lib.plotting.plot_info import AttrKey, DimKey, ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PolarMeshInfo, ScatterInfo

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


@overload
def _one_or_none[T](objs: Iterable[T], key: None = None) -> T | None: ...
def _one_or_none(objs: Iterable[Any], key: AttrKey | tuple[AttrKey, DimKey] | None = None) -> Any | None:
    if key is None:
        vals = set(objs)
    elif isinstance(key, str):
        vals = {getattr(obj, key, None) for obj in objs}
    else:
        vals = {getattr(obj, key[0], {}).get(key[1], None) for obj in objs}
    if len(vals) == 1:
        return vals.pop()
    return None


class UpdateTitle:
    def __init__(self, text: Text, plot_info: PlotInfo):
        self.text = text
        self.plot_info = plot_info

    def __call__(self, *_):
        self.text.set_text(self.plot_info.get_title())


class AxesManager(ABC):
    @abstractmethod
    def setup_title(self): ...

    @abstractmethod
    def setup_labels(self): ...

    @abstractmethod
    def setup_data(self): ...


class AxesManagerSingle[A: Axes, PI: PlotInfo](AxesManager):
    def __init__(self, ax: A, info: PI):
        self.ax = ax
        self.info = info

    def setup_title(self):
        update_title = UpdateTitle(self.ax.title, self.info)
        self.info._setter_callbacks["subject"] = update_title
        self.info._setter_callbacks["dim_displays"] = update_title
        self.info._setter_callbacks["dim_units"] = update_title
        self.info._setter_callbacks["scalar_coord_values"] = update_title
        update_title()


class AxesManagerSingle2D[PI2D: PlotInfo2D](AxesManagerSingle[Axes, PI2D]):
    def setup_labels(self):
        self.ax.set_xlabel(self.info.get_dim_label(self.info.x_dim))
        self.ax.set_ylabel(self.info.get_dim_label(self.info.y_dim))

    def setup_scales(self):
        self.ax.set_xscale(self.info.dim_scales[self.info.x_dim].to_axis_scale())
        self.ax.set_yscale(self.info.dim_scales[self.info.y_dim].to_axis_scale())

    def setup_bounds(self):
        self.ax.set_xbound(*self.info.dim_bounds[self.info.x_dim])
        self.ax.set_ybound(*self.info.dim_bounds[self.info.y_dim])


class AxesManagerSingleLine(AxesManagerSingle2D[LineInfo]):
    def setup_data(self):
        [line] = self.ax.plot(self.info.x_data, self.info.y_data, linestyle=self.info.line_style, scalex=False, scaley=False)
        self.info._setter_callbacks["x_data"] = line.set_xdata
        self.info._setter_callbacks["y_data"] = line.set_ydata
        self.info._setter_callbacks["line_style"] = line.set_linestyle

        self.setup_scales()
        self.setup_bounds()


class AxesManagerSingleImage(AxesManagerSingle2D[ImageInfo]):
    def setup_data(self):
        image = self.ax.imshow(
            self.info.data,
            origin="lower",
            extent=(*self.info.dim_bounds[self.info.x_dim], *self.info.dim_bounds[self.info.y_dim]),
            norm=self.info.dim_scales[self.info.color_dim].to_color_norm(),
            interpolation="nearest",
        )
        self.info._setter_callbacks["data"] = image.set_data

        self.ax.figure.colorbar(image)
        data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

        self.setup_scales()
        self.setup_bounds()

        self.ax.set_aspect(1 / self.ax.get_data_ratio())


class AxesManagerSingleScatter(AxesManagerSingle2D[ScatterInfo]):
    def setup_data(self):
        if self.info.color_dim:
            scatter = self.ax.scatter(
                self.info.x_data,
                self.info.y_data,
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
                self.info.x_data,
                self.info.y_data,
                color=self.ax._get_lines.get_next_color(),
                s=0.5,
            )

        update_data = lambda _=None: scatter.set_offsets(np.array([self.info.x_data, self.info.y_data]).T)
        self.info._setter_callbacks["x_data"] = update_data
        self.info._setter_callbacks["y_data"] = update_data

        self.setup_scales()
        self.setup_bounds()

        self.ax.set_aspect(1 / self.ax.get_data_ratio())


class AxesManagerSinglePolarMesh(AxesManagerSingle[PolarAxes, PolarMeshInfo]):
    def setup_labels(self):
        # FIXME make the labels work
        pass

    def setup_data(self):
        self.ax.set_rscale(self.info.dim_scales[self.info.r_dim].to_axis_scale())

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


def setup_fig(plot_infos: list[PlotInfo]) -> Figure:
    figure = plt.figure()

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
            raise NotImplementedError("don't yet support multiple plots per axes")

        manager.setup_title()
        manager.setup_labels()
        manager.setup_data()

    return figure
