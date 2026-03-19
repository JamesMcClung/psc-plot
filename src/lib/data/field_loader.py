import pscpy
import xarray as xr

from lib.data.data_with_attrs import Field, FieldMetadata

from .. import field_util, file_util
from ..derived_field_variables import derive_field_variable
from .source import DataSource


class FieldLoader(DataSource):
    def __init__(self, prefix: file_util.FieldPrefix, var_name: str, steps: list[int]):
        self.prefix = prefix
        self.var_name = var_name
        self.steps = steps

    def _preprocess(self, ds: xr.Dataset) -> xr.DataArray:
        ds = pscpy.decode_psc(ds, ["e", "i"])
        derive_field_variable(ds, self.var_name, self.prefix)
        return ds[self.var_name]

    def get_data(self) -> Field:
        da = xr.open_mfdataset(
            paths=[field_util.get_path(self.prefix, step) for step in self.steps],
            # TODO chunk by component?
            combine="nested",
            concat_dim="t",
            preprocess=self._preprocess,
        )
        metadata = FieldMetadata(
            var_name=self.get_var_name(),
            var_latex=f"\\text{{{self.var_name}}}",
            name_fragments=self.get_name_fragments(),
        )
        return Field(da, metadata)

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return self.var_name

    def get_name_fragments(self) -> list[str]:
        return [self.prefix, self.var_name]
