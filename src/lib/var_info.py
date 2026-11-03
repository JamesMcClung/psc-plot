from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field, replace
from typing import Literal

from lib.data.types import VarKey
from lib.scale import LinearScale, Scale

from .latex import Latex

RADIAN = Latex("\\text{rad}")

FOURIER_KEY_PREFIX = "k_"


type FourierAngle = Literal["rev", "rad"]
FOURIER_ANGLES: tuple[FourierAngle, ...] = ("rev", "rad")


def _fourier_unit(unit: Latex, angle: FourierAngle) -> Latex:
    angle_unit = f"\\text{{{angle}}}"
    inverse_suffix = "^{-1}"
    if not unit:
        return Latex(angle_unit)
    if unit.ends_with(inverse_suffix):
        return unit.remove_suffix(inverse_suffix).prepend(f"{angle_unit}\\,")
    return unit.prepend(f"{angle_unit}/")


type Geometry = Literal["linear", "polar:r", "polar:theta", "spherical:r", "spherical:theta", "spherical:phi"]


@dataclass(frozen=True)
class VarInfo:
    display: Latex
    unit: Latex
    geometry: Geometry | None = None
    _: KW_ONLY
    key: VarKey = None
    scale: Scale = field(default_factory=LinearScale)
    fourier_origin: FourierOrigin | None = None

    def __post_init__(self):
        if self.key is None:
            object.__setattr__(self, "key", self.display.plain)

    def assign(
        self,
        *,
        display: str | Latex | None = None,
        unit: str | Latex | None = None,
    ) -> VarInfo:
        if isinstance(display, str):
            display = Latex(display)
        if isinstance(unit, str):
            unit = Latex(unit)
        return replace(self, display=display or self.display, unit=unit or self.unit)

    def to_fourier(self, angle: FourierAngle) -> VarInfo:
        """The var-info of this dim's Fourier conjugate, in `angle`s per this dim's unit."""
        # TODO make t <-> omega
        return VarInfo(
            self.display.prepend(FOURIER_KEY_PREFIX),
            _fourier_unit(self.unit, angle),
            self.geometry,
            fourier_origin=FourierOrigin(angle, self),
        )

    def from_fourier(self) -> VarInfo:
        """The var-info this Fourier dim was transformed from."""
        if self.fourier_origin is None:
            raise ValueError(f"{self.key} is not a Fourier dimension")
        return self.fourier_origin.original

    @property
    def fourier_angle(self) -> FourierAngle | None:
        return self.fourier_origin and self.fourier_origin.angle

    def is_fourier(self) -> bool:
        return self.fourier_origin is not None


@dataclass(frozen=True)
class FourierOrigin:
    angle: FourierAngle
    original: VarInfo


def check_unit_compatibility(dim_1: VarInfo, dim_2: VarInfo, dest_geometry: str):
    if dim_1.unit != dim_2.unit:
        raise ValueError(f"Dimensions {dim_1.display} and {dim_2.display} have incompatible units for transforming to {dest_geometry} coordinates ({dim_1.unit} and {dim_2.unit})")
