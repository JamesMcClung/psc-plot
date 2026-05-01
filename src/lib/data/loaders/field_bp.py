import re
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

_KNOWN_PREFIXES = ("pfd", "pfd_moments", "gauss", "continuity")
_STEP_BP_RE = re.compile(r"^(.+?)\.\d+\.bp$")


def _get_path(prefix: str, step: int) -> Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.bp"


@loader
class FieldLoaderBp(DataSource):
    @classmethod
    def discover(cls, data_dir: Path) -> list[str]:
        present = {m.group(1) for entry in data_dir.iterdir() if (m := _STEP_BP_RE.match(entry.name))}
        return [p for p in _KNOWN_PREFIXES if p in present]

    def __init__(self, prefix: str, active_key: str | None = None):
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
