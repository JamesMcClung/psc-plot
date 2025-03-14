import typing

import numpy as np
import numpy.typing as npt
import pandas as pd

from .. import file_util, h5_util, plt_util
from .animation_base import Animation

__all__ = ["H5Animation", "PrtVariable", "PRT_VARIABLES", "NBins", "BinEdges"]

type PrtVariable = typing.Literal["x", "y", "z", "px", "py", "pz", "q", "m", "w", "id", "tag"]
PRT_VARIABLES: list[PrtVariable] = list(PrtVariable.__value__.__args__)

type NBins = int
type BinEdges = npt.NDArray[np.float64]


class H5Animation(Animation):
    def __init__(
        self,
        steps: list[int],
        prefix: file_util.H5Prefix,
        *,
        axis_variables: tuple[PrtVariable, PrtVariable],
        bins: tuple[NBins | BinEdges, NBins | BinEdges] | None,
    ):
        super().__init__(steps)

        self.prefix = prefix
        self.axis_variables = axis_variables

        df = h5_util.load_df(self.prefix, self.steps[0])

        binned_data, self.x_edges, self.y_edges = self._get_binned_data(df, bins)

        self.mesh = self.ax.pcolormesh(self.x_edges, self.y_edges, binned_data, cmap="inferno")

        self.fig.colorbar(self.mesh)
        plt_util.update_cbar(self.mesh)

        self.ax.set_xlabel(self.axis_variables[0])
        self.ax.set_ylabel(self.axis_variables[1])
        self.ax.set_title("reduced f")

    def _update_fig(self, step: int):
        df = h5_util.load_df(self.prefix, step)

        binned_data, _, _ = self._get_binned_data(df)

        self.mesh.set_array(binned_data)
        plt_util.update_cbar(self.mesh)

        return [self.mesh]

    def _get_binned_data(
        self,
        df: pd.DataFrame,
        bins: tuple[NBins | BinEdges, NBins | BinEdges] | None = None,
    ) -> tuple[npt.NDArray[np.float64], BinEdges, BinEdges]:
        binned_data, x_edges, y_edges = np.histogram2d(
            df[self.axis_variables[0]],
            df[self.axis_variables[1]],
            bins=bins or (self.x_edges, self.y_edges),
            weights=df["w"],
            density=True,
        )
        binned_data = binned_data.T

        return binned_data, x_edges, y_edges
