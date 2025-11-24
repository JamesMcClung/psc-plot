import xarray as xr

from .. import field_util, file_util
from ..derived_field_variables import derive_field_variable
from .keys import VAR_LATEX_KEY
from .source import DataSource


def _load_field_variable(prefix: file_util.FieldPrefix, step: int, var_name: str) -> xr.DataArray:
    ds = field_util.load_ds(prefix, step)
    ds = ds.assign_coords(t=ds.time)
    derive_field_variable(ds, var_name, prefix)

    return ds[var_name]


class FieldLoader(DataSource):
    def __init__(self, prefix: file_util.FieldPrefix, var_name: str):
        self.prefix = prefix
        self.var_name = var_name

    def get_data_at_step(self, step: int) -> xr.DataArray:
        return _load_field_variable(self.prefix, step, self.var_name)

    def get_data(self, steps: list[int]) -> xr.DataArray:
        da = xr.concat((self.get_data_at_step(step) for step in steps), "t")
        da.attrs[VAR_LATEX_KEY] = self.var_name
        return da

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return self.var_name

    def get_modified_var_name(self) -> str:
        return f"\\text{{{self.var_name}}}"

    def get_name_fragments(self) -> list[str]:
        return [self.prefix, self.var_name]
