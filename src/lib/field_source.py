import xarray as xr

from . import field_util, file_util
from .derived_field_variables import derive_field_variable

__all__ = ["load_field_variable"]


def load_field_variable(prefix: file_util.FieldPrefix, step: int, var_name: str) -> xr.DataArray:
    ds = field_util.load_ds(prefix, step)
    derive_field_variable(ds, var_name, prefix)

    da = ds[var_name]

    # TODO this is just to preserve time, which will eventually be a dimension
    da = da.assign_attrs(**ds.attrs)

    return da
