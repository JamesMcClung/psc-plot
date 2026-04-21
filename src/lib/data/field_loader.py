import pscpy
import xarray as xr

from lib.data.data_with_attrs import Field, FieldMetadata

from .. import field_util, file_util
from ..derived_field_variables import derive_field_variable
from ..var_info_registry import lookup
from .source import DataSource


class FieldLoader(DataSource):
    def __init__(self, prefix: file_util.FieldPrefix, active_key: str | None, steps: list[int]):
        self.prefix = prefix
        self.active_key = active_key
        self.steps = steps

    def get_data(self) -> Field:
        ds = xr.open_mfdataset(
            paths=[field_util.get_path(self.prefix, step) for step in self.steps],
            # TODO chunk by component?
            combine="nested",
            concat_dim="t",
            preprocess=lambda ds: pscpy.decode_psc(ds, ["e", "i"]),
        )
        if self.active_key is not None:
            derive_field_variable(ds, self.active_key, self.prefix)
        var_info = {key: lookup(self.prefix, key) for key in ds.variables}
        metadata = FieldMetadata(
            active_key=self.active_key,
            name_fragments=self.get_name_fragments(),
            prefix=self.prefix,
            var_infos=var_info,
        )
        return Field(ds, metadata)

    def get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.active_key is not None:
            fragments.append(self.active_key)
        return fragments
