import typing

import numpy as np

from lib.data.data_with_attrs import FullList
from lib.dimension import DIMENSIONS
from lib.parsing.fit import Fit
from lib.plotting import plt_util
from lib.plotting.animated_plot import AnimatedPlot


class AnimatedScatterPlot(AnimatedPlot[FullList]):
    def __init__(
        self,
        data: FullList,
        *,
        scales: list[plt_util.Scale] = [],
        subplot_kw: dict[str, typing.Any] = {},
    ):
        self.times = np.array(data.coordss[data.metadata.time_dim])
        super().__init__(data, scales=scales, subplot_kw=subplot_kw)

        self.dependent_var = data.metadata.dependent_var
        self.fits: list[Fit] = []

    def _get_nframes(self) -> int:
        return len(self.times)

    def _init_fig(self):
        data = self._get_data_at_frame(0)
        df = data.data

        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[0])

        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(f"${data.metadata.var_latex}$" if self.dependent_var == data.metadata.var_name else DIMENSIONS[self.dependent_var].to_axis_label())

        if data.metadata.color_dim:
            self.scatter = self.ax.scatter(df[self.spatial_dims[0]], df[self.dependent_var], c=df[data.metadata.color_dim], s=1)
        else:
            color = self.ax._get_lines.get_next_color()  # scatter() uses a different color cycler than plot(); this uses the plot() cycler manually
            self.scatter = self.ax.scatter(df[self.spatial_dims[0]], df[self.dependent_var], s=0.5, color=color)

        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if isinstance(pos, float)])

        self.fit_lines = [fit.plot_fit(self.ax, data) for fit in self.fits]
        if self.fits:
            self.ax.legend()

        if data.metadata.color_dim:
            # TODO update cbar
            self.fig.colorbar(self.scatter, label=DIMENSIONS[data.metadata.color_dim].to_axis_label())

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)
        df = data.data

        self.scatter.set_offsets(np.array([df[self.spatial_dims[0]], df[self.dependent_var]]).T)
        plt_util.update_title(self.ax, data.metadata.var_latex, [DIMENSIONS[dim].get_coordinate_label(pos) for dim, pos in data.coordss.items() if isinstance(pos, float)])

        for fit, line in zip(self.fits, self.fit_lines):
            # TODO properly add and remove lines from fits
            fit.update_fit(df, line)

        if self.fits:
            # updates legend in case fit labels changed (e.g. to show different fit params)
            self.ax.legend()

        return [self.scatter, self.ax.title]
