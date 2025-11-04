from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .latex import Latex

INVERSE_ELECTRON_PLASMA_FREQUENCY = Latex("\\omega_\\text{pe}^{-1}")
ELECTRON_SKIN_DEPTH = Latex("d_\\text{e}")
RADIAN = Latex("\\text{rad}")

FOURIER_NAME_PREFIX = "k_"


def _toggle_unit_fourier(unit: Latex) -> Latex:
    inverse_suffix = "^{-1}"
    if unit.ends_with(inverse_suffix):
        return unit.remove_suffix(inverse_suffix)
    else:
        return unit.append(inverse_suffix)


@dataclass(frozen=True)
class Dimension:
    name: Latex
    unit: Latex
    geometry: typing.Literal["cartesian", "temporal", "polar:r", "polar:theta", "spherical:r", "spherical:theta", "spherical:phi"]

    def to_axis_label(self) -> str:
        return f"${self.name.latex}\\ [{self.unit.latex}]$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.name.latex} = {coord_val:.3f}\\ {self.unit.latex}$"

    def toggle_fourier(self) -> Dimension:
        # TODO make t <-> omega
        toggled_unit = _toggle_unit_fourier(self.unit)
        if self.is_fourier():
            return Dimension(self.name.remove_prefix(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)
        else:
            return Dimension(self.name.prepend(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)

    def is_fourier(self) -> bool:
        return self.name.starts_with(FOURIER_NAME_PREFIX)

    def register(self) -> typing.Self:
        DIMENSIONS[self.name.plain] = self
        return self


class Transform2D(ABC):
    @abstractmethod
    def apply[T: float | npt.NDArray[np.float64]](self, c1: T, c2: T) -> tuple[T, T]: ...


class Transform3D(ABC):
    @abstractmethod
    def apply[T: float | npt.NDArray[np.float64]](self, c1: T, c2: T, c3: T) -> tuple[T, T, T]: ...


def check_unit_compatability(dim_1: Dimension, dim_2: Dimension, dest_geometry: str):
    if dim_1.unit != dim_2.unit:
        raise ValueError(f"Dimensions {dim_1.name} and {dim_2.name} have incompatible units for transforming to {dest_geometry} coordinates ({dim_1.unit} and {dim_2.unit})")


class CartesianToPolar(Transform2D):
    def __init__(self, dim_x: Dimension, dim_y: Dimension):
        check_unit_compatability(dim_x, dim_y, "polar")

        self.dim_x = dim_x
        self.dim_y = dim_y
        r_name = "k" if dim_x.is_fourier() else "r"
        self.dim_r = Dimension(Latex(r_name), dim_x.unit, "polar:r").register()
        self.dim_theta = Dimension(Latex("\\theta"), RADIAN, "polar:theta").register()

    def apply[T: float | npt.NDArray[np.float64]](self, x: T, y: T) -> tuple[T, T]:
        r = (x**2 + y**2) ** 0.5
        theta = np.arctan2(y, x)
        return (r, theta)

    def inverse[T: float | npt.NDArray[np.float64]](self, r: T, theta: T) -> tuple[T, T]:
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        return (x, y)


class CartesianToSpherical(Transform3D):
    def __init__(self, dim_x: Dimension, dim_y: Dimension, dim_z: Dimension):
        check_unit_compatability(dim_x, dim_y, "spherical")
        check_unit_compatability(dim_x, dim_z, "spherical")

        self.dim_x = dim_x
        self.dim_y = dim_y
        self.dim_z = dim_z
        r_name = "k" if dim_x.is_fourier() else "r"
        self.dim_r = Dimension(Latex(r_name), dim_x.unit, "spherical:r").register()
        self.dim_theta = Dimension(Latex("\\theta"), RADIAN, "spherical:theta").register()
        self.dim_phi = Dimension(Latex("\\phi"), RADIAN, "spherical:phi").register()

    def apply[T: float | npt.NDArray[np.float64]](self, x: T, y: T, z: T) -> tuple[T, T, T]:
        rho2 = x**2 + y**2
        r = (rho2 + z**2) ** 0.5
        theta = np.arctan2(z, rho2**0.5)
        phi = np.arctan2(y, x)
        return (r, theta, phi)

    def inverse[T: float | npt.NDArray[np.float64]](self, r: T, theta: T, phi: T) -> tuple[T, T, T]:
        x = r * np.cos(theta) * np.cos(phi)
        y = r * np.cos(theta) * np.sin(phi)
        z = r * np.sin(theta)
        return (x, y, z)


DIMENSIONS: dict[str, Dimension] = {}


Dimension(Latex("x"), ELECTRON_SKIN_DEPTH, "cartesian").register()
Dimension(Latex("y"), ELECTRON_SKIN_DEPTH, "cartesian").register()
Dimension(Latex("z"), ELECTRON_SKIN_DEPTH, "cartesian").register()
Dimension(Latex("t"), INVERSE_ELECTRON_PLASMA_FREQUENCY, "temporal").register()

for dim in ["x", "y", "z"]:
    DIMENSIONS[dim].toggle_fourier().register()
