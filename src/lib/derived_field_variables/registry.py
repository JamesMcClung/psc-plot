import numpy as np
import pscpy
from xarray import DataArray, Dataset

from .derived_field_variable import derived_field_variable

__all__ = []


@derived_field_variable("pfd_moments")
def rho(rho_i: DataArray, rho_e: DataArray) -> DataArray:
    return rho_i + rho_e


@derived_field_variable("gauss")
def error(rho: DataArray, dive: DataArray) -> DataArray:
    return rho - dive


@derived_field_variable("continuity")
def error(d_rho: DataArray, dt_divj: DataArray) -> DataArray:
    return d_rho + dt_divj


@derived_field_variable("pfd")
def h2_cc(hx_fc: DataArray, hy_fc: DataArray, hz_fc: DataArray) -> DataArray:
    h = Dataset({"hx_fc": hx_fc, "hy_fc": hy_fc, "hz_fc": hz_fc})
    pscpy.auto_recenter(h, "cc", x="periodic", y="periodic", z="periodic")
    return h["hx_cc"] ** 2 + h["hy_cc"] ** 2 + h["hz_cc"] ** 2


@derived_field_variable("pfd")
def h_cc(h2_cc: DataArray) -> DataArray:
    return np.sqrt(h2_cc)
