from pathlib import Path

import pscpy
import xarray as xr

from lib.config import CONFIG
from lib.data.data_with_attrs import Field, FieldMetadata
from lib.data.loader_registry import loader
from lib.data.source import DataSource
from lib.derived_field_variables import derive_field_variable
from lib.file_util import get_available_steps
from lib.var_info_registry import lookup


def _get_path(prefix: str, step: int) -> Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.bp"


@loader("pfd", "pfd_moments", "gauss", "continuity")
class FieldLoaderBp(DataSource):
    def __init__(self, prefix: str, active_key: str | None):
        self.prefix = prefix
        self.active_key = active_key
        self.steps = get_available_steps(f"{prefix}.", ".bp")

    def get_data(self) -> Field:
        ds = xr.open_mfdataset(
            paths=[_get_path(self.prefix, step) for step in self.steps],
            combine="nested",
            concat_dim="t",
            preprocess=lambda ds: pscpy.decode_psc(ds, ["e", "i"]),
        )
        if self.active_key is not None:
            derive_field_variable(ds, self.active_key, self.prefix)
        var_info = {key: lookup(self.prefix, key) for key in ds.variables}
        metadata = FieldMetadata(
            active_key=self.active_key,
            name_fragments=self._get_name_fragments(),
            prefix=self.prefix,
            var_infos=var_info,
        )
        return Field(ds, metadata)

    def _get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.active_key is not None:
            fragments.append(self.active_key)
        return fragments
