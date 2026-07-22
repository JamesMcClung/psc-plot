from abc import ABC, abstractmethod
from dataclasses import KW_ONLY, dataclass, field

type DimKey = str


@dataclass
class SpatialDims(ABC):
    ndims: int

    @abstractmethod
    def unpack(self) -> tuple[DimKey, DimKey]: ...


@dataclass
class SpatialDimsXY(SpatialDims):
    x_dim: DimKey
    y_dim: DimKey
    ndims: int = field(default=2, init=False)

    def unpack(self):
        return (self.x_dim, self.y_dim)


@dataclass
class SpatialDimsRTheta(SpatialDims):
    r_dim: DimKey
    theta_dim: DimKey
    ndims: int = field(default=2, init=False)

    def unpack(self):
        return (self.r_dim, self.theta_dim)


@dataclass
class PlotTarget:
    prefix: str
    _: KW_ONLY
    spatial_dims: SpatialDims
    color_dim: DimKey | None = None
    time_dim: DimKey | None = None

    axes_index: tuple[int, int] = (1, 1)  # 1-based
