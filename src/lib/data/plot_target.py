from dataclasses import KW_ONLY, dataclass, field

type DimKey = str


@dataclass
class SpatialDims:
    ndims: int


@dataclass
class SpatialDimsXY(SpatialDims):
    x_dim: DimKey
    y_dim: DimKey
    ndims: int = field(default=2, init=False)


@dataclass
class SpatialDimsRTheta(SpatialDims):
    r_dim: DimKey
    theta_dim: DimKey
    ndims: int = field(default=2, init=False)


@dataclass
class PlotTarget:
    prefix: str
    _: KW_ONLY
    spatial_dims: SpatialDims
    color_dim: DimKey | None = None
    time_dim: DimKey | None = None

    axes_index: tuple[int, int] = (1, 1)  # 1-based
