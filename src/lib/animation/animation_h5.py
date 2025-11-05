import numpy as np
import numpy.typing as npt
import pandas as pd

from .. import file_util, h5_util, plt_util
from ..adaptors import PluginH5
from ..h5_util import PrtVariable
from .animation_base import Animation

__all__ = ["H5Animation", "NBins", "BinEdges"]


type NBins = int
type BinEdges = npt.NDArray[np.float64]


class H5Animation(Animation):
    def __init__(
        self,
        steps: list[int],
        prefix: file_util.H5Prefix,
        *,
        axis_variables: tuple[PrtVariable, PrtVariable],
        nicell: int,
        bins: tuple[NBins | BinEdges, NBins | BinEdges] | None = None,
    ):
        super().__init__(steps)

        self.prefix = prefix
        self.plugins: list[PluginH5] = []
        self.axis_variables = axis_variables
        self._nicell = nicell
        self._bins = bins

    def add_plugin(self, plugin: PluginH5):
        self.plugins.append(plugin)

    def _init_fig(self):
        binned_data, self.x_edges, self.y_edges = self._get_binned_data(self.steps[0], self._bins or self._guess_bins())

        self.mesh = self.ax.pcolormesh(self.x_edges, self.y_edges, binned_data, cmap="inferno")

        self.fig.colorbar(self.mesh)
        plt_util.update_cbar(self.mesh)

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(self.axis_variables[0])
        self.ax.set_ylabel(self.axis_variables[1])
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
        df = h5_util.load_df(self.prefix, step)

        for plugin in self.plugins:
            df = plugin.apply(df)

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
        plugin_name_fragments = [p.get_name_fragment() for p in self.plugins]
        plugin_name_fragments = [frag for frag in plugin_name_fragments if frag]
        return "-".join([self.prefix] + list(self.axis_variables) + plugin_name_fragments) + ".mp4"
