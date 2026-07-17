import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes

from lib.plotting import plt_util
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PolarMeshInfo, ScatterInfo

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


class UpdateTitle:
    def __init__(self, ax: Axes, plot_infos: list[PlotInfo]):
        self.ax = ax
        self.plot_infos = plot_infos

    def __call__(self, *_):
        assert len(self.plot_infos) == 1
        self.ax.set_title(self.plot_infos[0].get_title())


def setup_fig(plot_infos: list[PlotInfo]) -> Figure:
    figure = plt.figure()

    for ax, infos in _setup_axes(figure, plot_infos).values():
        assert len(infos) == 1  # TODO remove
        [plot_info] = infos

        # note: must avoid lambdas in loop, since they don't capture
        update_title = UpdateTitle(ax, infos)
        plot_info._setter_callbacks["subject"] = update_title
        plot_info._setter_callbacks["dim_displays"] = update_title
        plot_info._setter_callbacks["dim_units"] = update_title
        plot_info._setter_callbacks["scalar_coord_values"] = update_title
        update_title()

        if isinstance(plot_info, PlotInfo2D):
            ax.set_xlabel(plot_info.get_dim_label(plot_info.x_dim))
            ax.set_ylabel(plot_info.get_dim_label(plot_info.y_dim))

        if isinstance(plot_info, LineInfo):
            [line] = ax.plot(plot_info.x_data, plot_info.y_data, linestyle=plot_info.line_style, scalex=False, scaley=False)
            plot_info._setter_callbacks["x_data"] = line.set_xdata
            plot_info._setter_callbacks["y_data"] = line.set_ydata
            plot_info._setter_callbacks["line_style"] = line.set_linestyle

        if isinstance(plot_info, ImageInfo):
            image = ax.imshow(
                plot_info.data,
                origin="lower",
                extent=(*plot_info.dim_bounds[plot_info.x_dim], *plot_info.dim_bounds[plot_info.y_dim]),
                norm=plot_info.dim_scales[plot_info.color_dim].to_color_norm(),
                interpolation="nearest",
            )
            plot_info._setter_callbacks["data"] = image.set_data

            figure.colorbar(image)
            data_lower, data_upper = plot_info.dim_bounds[plot_info.color_dim]
            plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

        if isinstance(plot_info, ScatterInfo):
            if plot_info.color_dim:
                scatter = ax.scatter(
                    plot_info.x_data,
                    plot_info.y_data,
                    c=plot_info.color_data,
                    norm=plot_info.dim_scales[plot_info.color_dim].to_color_norm(),
                    s=1,
                )
                plot_info._setter_callbacks["color_data"] = scatter.set_array

                figure.colorbar(scatter, label=plot_info.get_dim_label(plot_info.color_dim))
                data_lower, data_upper = plot_info.dim_bounds[plot_info.color_dim]
                plt_util.update_cbar(scatter, data_min_override=data_lower, data_max_override=data_upper)
            else:
                scatter = ax.scatter(
                    plot_info.x_data,
                    plot_info.y_data,
                    color=ax._get_lines.get_next_color(),
                    s=0.5,
                )

            update_data = lambda _=None: scatter.set_offsets(np.array([plot_info.x_data, plot_info.y_data]).T)
            plot_info._setter_callbacks["x_data"] = update_data
            plot_info._setter_callbacks["y_data"] = update_data

        if isinstance(plot_info, PlotInfo2D):
            ax.set_xscale(plot_info.dim_scales[plot_info.x_dim].to_axis_scale())
            ax.set_yscale(plot_info.dim_scales[plot_info.y_dim].to_axis_scale())

            ax.set_xbound(*plot_info.dim_bounds[plot_info.x_dim])
            ax.set_ybound(*plot_info.dim_bounds[plot_info.y_dim])

        if isinstance(plot_info, (ScatterInfo, ImageInfo)):
            ax.set_aspect(1 / ax.get_data_ratio())

        if isinstance(plot_info, PolarMeshInfo):
            # FIXME make the labels work
            ax: PolarAxes

            ax.set_rscale(plot_info.dim_scales[plot_info.r_dim].to_axis_scale())

            image = ax.pcolormesh(
                *np.meshgrid(plot_info.theta_vertices, plot_info.r_vertices),
                plot_info.data,
                shading="flat",
                norm=plot_info.dim_scales[plot_info.color_dim].to_color_norm(),
            )
            plot_info._setter_callbacks["data"] = image.set_array

            figure.colorbar(image)
            data_lower, data_upper = plot_info.dim_bounds[plot_info.color_dim]
            plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

    return figure
