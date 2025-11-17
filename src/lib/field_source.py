import xarray as xr

from . import field_util, file_util
from .derived_field_variables import derive_field_variable

__all__ = ["load_field_variable"]


def load_field_variable(prefix: file_util.FieldPrefix, step: int, var_name: str) -> xr.DataArray:
    ds = field_util.load_ds(prefix, step)
    ds = ds.assign_coords(t=ds.time)
    derive_field_variable(ds, var_name, prefix)

    return ds[var_name]
