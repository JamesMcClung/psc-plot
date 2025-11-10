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


@derived_particle_variable("prt")
def w_x(m: Series, px: Series) -> Series:
    return 0.5 * m * px**2


@derived_particle_variable("prt")
def w_y(m: Series, py: Series) -> Series:
    return 0.5 * m * py**2


@derived_particle_variable("prt")
def w_z(m: Series, pz: Series) -> Series:
    return 0.5 * m * pz**2


@derived_particle_variable("prt")
def w_xy(m: Series, px: Series, py: Series) -> Series:
    return 0.5 * m * (px**2 + py**2)


@derived_particle_variable("prt")
def w_yz(m: Series, py: Series, pz: Series) -> Series:
    return 0.5 * m * (py**2 + pz**2)


@derived_particle_variable("prt")
def w_zx(m: Series, pz: Series, px: Series) -> Series:
    return 0.5 * m * (pz**2 + px**2)


@derived_particle_variable("prt")
def w_xyz(m: Series, px: Series, py: Series, pz: Series) -> Series:
    return 0.5 * m * (px**2 + py**2 + pz**2)
