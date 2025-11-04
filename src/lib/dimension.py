from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

INVERSE_ELECTRON_PLASMA_FREQUENCY = "\\omega_\\text{pe}^{-1}"
ELECTRON_SKIN_DEPTH = "d_\\text{e}"
RADIAN = "\\text{rad}"

FOURIER_NAME_PREFIX = "k_"


def _toggle_unit_fourier(unit: str) -> str:
    inverse_suffix = "^{-1}"
    if unit.endswith(inverse_suffix):
        return unit.removesuffix(inverse_suffix)
    else:
        return unit + inverse_suffix


@dataclass(frozen=True)
class Dimension:
    name: str  # latex-formated, sans '$'
    unit: str  # latex-formated, sans '$'
    geometry: typing.Literal["cartesian", "temporal", "polar:r", "polar:theta"]

    def to_axis_label(self) -> str:
        return f"${self.name}\\ [{self.unit}]$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.name} = {coord_val:.3f}\\ {self.unit}$"

    def toggle_fourier(self) -> Dimension:
        # TODO make t <-> omega
        toggled_unit = _toggle_unit_fourier(self.unit)
        if self.is_fourier():
            return Dimension(self.name.removeprefix(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)
        else:
            return Dimension(FOURIER_NAME_PREFIX + self.name, toggled_unit, self.geometry)

    def is_fourier(self) -> bool:
        return self.name.startswith(FOURIER_NAME_PREFIX)

    def register(self) -> typing.Self:
        DIMENSIONS[self.name] = self
        return self


class Transform2D(ABC):
    @abstractmethod
    def apply[T: float | npt.NDArray[np.float64]](self, c1: T, c2: T) -> tuple[T, T]: ...


class CartesianToPolar(Transform2D):
    def __init__(self, dim_x: Dimension, dim_y: Dimension):
        if dim_x.unit != dim_y.unit:
            raise ValueError("Incompatible units for coordinate transform")

        self.dim_x = dim_x
        self.dim_y = dim_y
        self.dim_r = Dimension("r", dim_x.unit, "polar:r").register()
        self.dim_theta = Dimension("\\theta", RADIAN, "polar:theta").register()

    def apply[T: float | npt.NDArray[np.float64]](self, x: T, y: T) -> tuple[T, T]:
        r = (x**2 + y**2) ** 0.5
        theta = np.arctan2(y, x)
        return (r, theta)

    def inverse[T: float | npt.NDArray[np.float64]](self, r: T, theta: T) -> tuple[T, T]:
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        return (x, y)


DIMENSIONS: dict[str, Dimension] = {}


Dimension("x", ELECTRON_SKIN_DEPTH, "cartesian").register()
Dimension("y", ELECTRON_SKIN_DEPTH, "cartesian").register()
Dimension("z", ELECTRON_SKIN_DEPTH, "cartesian").register()
Dimension("t", INVERSE_ELECTRON_PLASMA_FREQUENCY, "temporal").register()

for dim in ["x", "y", "z"]:
    DIMENSIONS[dim].toggle_fourier().register()
