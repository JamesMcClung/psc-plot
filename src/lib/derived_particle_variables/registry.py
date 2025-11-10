from pandas import Series

from .derived_particle_variable import derived_particle_variable

__all__ = []


@derived_particle_variable("prt")
def pxy(px: Series, py: Series) -> Series:
    return (px**2 + py**2) ** 0.5


@derived_particle_variable("prt")
def pzx(py: Series, pz: Series) -> Series:
    return (py**2 + pz**2) ** 0.5


@derived_particle_variable("prt")
def pzx(pz: Series, px: Series) -> Series:
    return (pz**2 + px**2) ** 0.5


@derived_particle_variable("prt")
def anisotropy_y_zx(py: Series, pzx: Series) -> Series:
    return py / pzx
