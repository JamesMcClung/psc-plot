import typing

import numpy as np
import pandas as pd

from lib.data.keys import COLOR_DIM_KEY, DEPENDENT_VAR_KEY, TIME_DIM_KEY, VAR_LATEX_KEY
from lib.dimension import DIMENSIONS
from lib.parsing.fit import Fit
from lib.plotting import plt_util
from lib.plotting.animated_plot import AnimatedPlot


class AnimatedScatterPlot(AnimatedPlot[pd.DataFrame]):
    def __init__(
        self,
        data: pd.DataFrame,
        *,
        scales: list[plt_util.Scale] = [],
        subplot_kw: dict[str, typing.Any] = {},
    ):
        self.times = sorted(set(data[data.attrs[TIME_DIM_KEY]]))
        super().__init__(data, scales=scales, subplot_kw=subplot_kw)

        self.dependent_var = data.attrs[DEPENDENT_VAR_KEY]
        self.fits: list[Fit] = []

    def _get_nframes(self) -> int:
        return len(self.times)

    def _init_fig(self):
        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[0])

        self.ax.set_xlabel(DIMENSIONS[self.spatial_dims[0]].to_axis_label())
        self.ax.set_ylabel(f"${self.data.attrs[VAR_LATEX_KEY]}$" if self.dependent_var == DEPENDENT_VAR_KEY else DIMENSIONS[self.dependent_var].to_axis_label())

        data = self._get_data_at_frame(0)
        if data.attrs[COLOR_DIM_KEY]:
            self.scatter = self.ax.scatter(data[self.spatial_dims[0]], data[self.dependent_var], c=data[data.attrs[COLOR_DIM_KEY]], s=1)
        else:
            color = self.ax._get_lines.get_next_color()  # scatter() uses a different color cycler than plot(); this uses the plot() cycler manually
            self.scatter = self.ax.scatter(data[self.spatial_dims[0]], data[self.dependent_var], s=0.5, color=color)

        plt_util.update_title(self.ax, self.data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(self.times[0]))

        self.fit_lines = [fit.plot_fit(self.ax, data) for fit in self.fits]
        if self.fits:
            self.ax.legend()

        if data.attrs[COLOR_DIM_KEY]:
            # TODO update cbar
            self.fig.colorbar(self.scatter, label=DIMENSIONS[data.attrs[COLOR_DIM_KEY]].to_axis_label())

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.fig.tight_layout()

    def _update_fig(self, frame: int):
        data = self._get_data_at_frame(frame)
        self.scatter.set_offsets(np.array([data[self.spatial_dims[0]], data[self.dependent_var]]).T)
        plt_util.update_title(self.ax, self.data.attrs[VAR_LATEX_KEY], DIMENSIONS[self.time_dim].get_coordinate_label(self.times[frame]))

        for fit, line in zip(self.fits, self.fit_lines):
            # TODO properly add and remove lines from fits
            fit.update_fit(data, line)

        if self.fits:
            # updates legend in case fit labels changed (e.g. to show different fit params)
            self.ax.legend()

        return [self.scatter, self.ax.title]

    def _get_data_at_frame(self, frame: int) -> pd.DataFrame:
        return self.data[self.data[self.time_dim] == self.times[frame]]
