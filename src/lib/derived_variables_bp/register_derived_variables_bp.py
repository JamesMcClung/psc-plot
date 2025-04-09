from xarray import DataArray

from .registry import derived_variable_bp

__all__ = []


@derived_variable_bp("pfd_moments")
def rho(rho_i: DataArray, rho_e: DataArray) -> DataArray:
    return rho_i + rho_e
