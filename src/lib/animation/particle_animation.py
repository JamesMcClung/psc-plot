import typing

import numpy as np
import numpy.typing as npt
import pandas as pd

from .. import file_util, particle_util, plt_util
from ..adaptors import ParticlePipeline
from ..derived_particle_variables import derive_particle_variable
from ..particle_util import PrtVariable
from .animation_base import Animation

__all__ = ["ParticleAnimation", "NBins", "BinEdges", "Scale", "SCALES"]


type NBins = int
type BinEdges = npt.NDArray[np.float64]


type Scale = typing.Literal["linear", "log", "symlog"]
SCALES: list[Scale] = list(Scale.__value__.__args__)


class ParticleAnimation(Animation):
    def __init__(
        self,
        steps: list[int],
        prefix: file_util.ParticlePrefix,
        pipeline: ParticlePipeline,
        *,
        axis_variables: tuple[PrtVariable, PrtVariable],
        nicell: int,
        bins: tuple[NBins | BinEdges, NBins | BinEdges] | None = None,
        scales: list[Scale],
    ):
        super().__init__(steps)

        self.prefix = prefix
        self.pipeline = pipeline
        self.axis_variables = axis_variables
        self._nicell = nicell
        self._bins = bins
        self.scales = scales + ["linear"] * (1 + len(axis_variables) - len(scales))  # dep scale, then axis scales

        assert len(self.scales) == 1 + len(self.axis_variables)

    def _init_fig(self):
        binned_data, self.x_edges, self.y_edges = self._get_binned_data(self.steps[0], self._bins or self._guess_bins())

        self.mesh = self.ax.pcolormesh(
            self.x_edges,
            self.y_edges,
            binned_data,
            cmap="inferno",
            norm=self.scales[0],
        )

        self.fig.colorbar(self.mesh)
        plt_util.update_cbar(self.mesh)

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(self.axis_variables[0])
        self.ax.set_ylabel(self.axis_variables[1])

        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[2])

        self.ax.set_title("reduced f")

    def _update_fig(self, step: int):
        binned_data, _, _ = self._get_binned_data(step)

        self.mesh.set_array(binned_data)
        plt_util.update_cbar(self.mesh)

        return [self.mesh]

    def _guess_bins(self) -> tuple[BinEdges, BinEdges]:
        df_final = self._load_df(self.steps[-1])
        xmin = df_final[self.axis_variables[0]].min()
        xmax = df_final[self.axis_variables[0]].max()
        ymin = df_final[self.axis_variables[1]].min()
        ymax = df_final[self.axis_variables[1]].max()
        return (np.linspace(xmin, xmax, 100, endpoint=True), np.linspace(ymin, ymax, 100, endpoint=True))

    def _load_df(self, step: int) -> pd.DataFrame:
        df = particle_util.load_df(self.prefix, step)

        for var in self.axis_variables:
            derive_particle_variable(df, var, self.prefix)

        df = self.pipeline.apply(df)

        return df

    def _get_binned_data(
        self,
        step: int,
        bins: tuple[NBins | BinEdges, NBins | BinEdges] | None = None,
    ) -> tuple[npt.NDArray[np.float64], BinEdges, BinEdges]:
        df = self._load_df(step)

        binned_data, x_edges, y_edges = np.histogram2d(
            df[self.axis_variables[0]],
            df[self.axis_variables[1]],
            bins=bins or (self.x_edges, self.y_edges),
            weights=df["w"] / self._nicell,
        )
        binned_data = binned_data.T

        # FIXME the binned data cmap is not normalized correctly
        # it should satisfy $\int binned_data dV' = N_particles (in psc units)$
        return binned_data, x_edges, y_edges

    def _get_default_save_path(self) -> str:
        adaptor_name_fragments = self.pipeline.get_name_fragments()
        return "-".join([self.prefix] + list(self.axis_variables) + adaptor_name_fragments) + ".mp4"
