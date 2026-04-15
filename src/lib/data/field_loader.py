import pscpy
import xarray as xr

from lib.data.data_with_attrs import Field, FieldMetadata

from .. import field_units, field_util, file_util
from ..derived_field_variables import derive_field_variable
from .source import DataSource


class FieldLoader(DataSource):
    def __init__(self, prefix: file_util.FieldPrefix, var_name: str, steps: list[int]):
        self.prefix = prefix
        self.var_name = var_name
        self.steps = steps

    def get_data(self) -> Field:
        ds = xr.open_mfdataset(
            paths=[field_util.get_path(self.prefix, step) for step in self.steps],
            # TODO chunk by component?
            combine="nested",
            concat_dim="t",
            preprocess=lambda ds: pscpy.decode_psc(ds, ["e", "i"]),
        )
        derive_field_variable(ds, self.var_name, self.prefix)

        info = field_units.lookup_field(self.prefix, self.var_name)
        metadata = FieldMetadata(
            var_name=self.get_var_name(),
            display_latex=info.display_latex,
            unit_latex=info.unit_latex,
            name_fragments=self.get_name_fragments(),
            prefix=self.prefix,
        )
        return Field(ds, metadata)

    def get_file_prefix(self) -> str:
        return self.prefix

    def get_var_name(self) -> str:
        return self.var_name

    def get_name_fragments(self) -> list[str]:
        return [self.prefix, self.var_name]
