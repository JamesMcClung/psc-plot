import pscpy
import xarray as xr

from lib.data.data_with_attrs import Field, FieldMetadata
from lib.dimension import get_default_dim

from .. import field_units, field_util, file_util
from ..field_units import lookup
from ..derived_field_variables import derive_field_variable
from .source import DataSource


class FieldLoader(DataSource):
    def __init__(self, prefix: file_util.FieldPrefix, var_name: str | None, steps: list[int]):
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
        if self.var_name is not None:
            derive_field_variable(ds, self.var_name, self.prefix)
            info = field_units.lookup_field(self.prefix, self.var_name)
            display_latex = info.display_latex
            unit_latex = info.unit_latex
        else:
            display_latex = None
            unit_latex = None
        dims = {key: get_default_dim(key) for key in ds.coords.keys()}
        var_info = {key: lookup(self.prefix, key) for key in ds.variables}
        metadata = FieldMetadata(
            var_name=self.var_name,
            display_latex=display_latex,
            unit_latex=unit_latex,
            name_fragments=self.get_name_fragments(),
            prefix=self.prefix,
            dims=dims,
            var_info=var_info,
        )
        return Field(ds, metadata)

    def get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.var_name is not None:
            fragments.append(self.var_name)
        return fragments
