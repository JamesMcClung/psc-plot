from abc import ABC, abstractmethod
from dataclasses import KW_ONLY, dataclass, field

from lib.data.data_with_attrs import DataWithAttrs
from lib.data.types import VarKey


@dataclass
class SpatialDims(ABC):
    ndims: int

    @abstractmethod
    def unpack(self) -> tuple[VarKey, VarKey]: ...


@dataclass
class SpatialDimsXY(SpatialDims):
    x_dim: VarKey
    y_dim: VarKey
    ndims: int = field(default=2, init=False)

    def unpack(self):
        return (self.x_dim, self.y_dim)


@dataclass
class SpatialDimsRTheta(SpatialDims):
    r_dim: VarKey
    theta_dim: VarKey
    ndims: int = field(default=2, init=False)

    def unpack(self):
        return (self.r_dim, self.theta_dim)


@dataclass
class PlotTarget[D: DataWithAttrs = DataWithAttrs, SD: SpatialDims = SpatialDims]:
    data: D
    _: KW_ONLY
    spatial_dims: SD
    color_dim: VarKey | None = None
    time_dim: VarKey | None = None

    axes_loc: tuple[int, int] = (1, 1)  # 1-based
