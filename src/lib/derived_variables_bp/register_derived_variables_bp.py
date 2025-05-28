from xarray import DataArray

from .registry import derived_variable_bp

__all__ = []


@derived_variable_bp("pfd_moments")
def rho(rho_i: DataArray, rho_e: DataArray) -> DataArray:
    return rho_i + rho_e


@derived_variable_bp("gauss")
def error(rho: DataArray, dive: DataArray) -> DataArray:
    return rho - dive


@derived_variable_bp("continuity")
def error(d_rho: DataArray, dt_divj: DataArray) -> DataArray:
    return d_rho + dt_divj
