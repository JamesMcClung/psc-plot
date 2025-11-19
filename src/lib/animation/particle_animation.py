import numpy as np
import numpy.typing as npt
from matplotlib.colors import SymLogNorm

from .. import plt_util
from ..data.particle_loader import ParticleLoader
from .animation_base import Animation
from .field_animation import get_extent

__all__ = ["ParticleAnimation", "NBins", "BinEdges"]


type NBins = int
type BinEdges = npt.NDArray[np.float64]


class ParticleAnimation(Animation):
    def __init__(
        self,
        steps: list[int],
        loader: ParticleLoader,
        *,
        scales: list[plt_util.Scale],
    ):
        super().__init__(len(steps))

        self.steps = steps
        self.loader = loader
        self.scales = scales + ["linear"] * (3 - len(scales))  # dep scale, then axis scales
        self.data = self.loader.get_data(steps)

    def _init_fig(self):
        data = self.data.isel(t=0)

        if self.scales[0] == "symlog":
            self.scales[0] = SymLogNorm(linthresh=1e-8)

        self.im = self.ax.imshow(
            data.T,
            origin="lower",
            extent=(*get_extent(data, data.dims[0]), *get_extent(data, data.dims[1])),
            norm=self.scales[0],
        )

        self.fig.colorbar(self.im)
        plt_util.update_cbar(self.im)

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(self.data.dims[0])
        self.ax.set_ylabel(self.data.dims[1])

        self.ax.set_xscale(self.scales[1])
        self.ax.set_yscale(self.scales[2])

        self.ax.set_title(self.loader.get_modified_var_name())

    def _update_fig(self, frame: int):
        data = self.data.isel(t=frame)

        self.im.set_array(data.T)
        plt_util.update_cbar(self.im)

        return [self.im]

    def _get_default_save_path(self) -> str:
        return "-".join(self.loader.get_name_fragments()) + ".mp4"
