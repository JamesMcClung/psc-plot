import xarray as xr

from .. import field_util, file_util
from ..derived_field_variables import derive_field_variable
from .keys import NAME_FRAGMENTS_KEY, VAR_LATEX_KEY
from .source import DataSource


def _load_field_variable(prefix: file_util.FieldPrefix, step: int, var_name: str) -> xr.DataArray:
    ds = field_util.load_ds(prefix, step)
    ds = ds.assign_coords(t=ds.time)
    for da_name in ds:
        ds[da_name].attrs = {
            VAR_LATEX_KEY: f"\\text{{{da_name}}}",
            NAME_FRAGMENTS_KEY: [],
        }
    derive_field_variable(ds, var_name, prefix)

    return ds[var_name]


class FieldLoader(DataSource):
    def __init__(self, prefix: file_util.FieldPrefix, var_name: str, steps: list[int]):
        self.prefix = prefix
        self.var_name = var_name
        self.steps = steps

    def get_data(self) -> xr.DataArray:
        da = xr.concat((_load_field_variable(self.prefix, step, self.var_name) for step in self.steps), "t")
        da.attrs = {
            VAR_LATEX_KEY: f"\\text{{{self.var_name}}}",
            NAME_FRAGMENTS_KEY: self.get_name_fragments(),
        }
        return da

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return self.var_name

    def get_name_fragments(self) -> list[str]:
        return [self.prefix, self.var_name]
