import re
from pathlib import Path

import pscpy
import xarray as xr

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.data_with_attrs import Field, FieldMetadata
from lib.data.loader import Loader, loader
from lib.derived_field_variables import derive_field_variable
from lib.var_info_registry import lookup

_KNOWN_PREFIXES = ("pfd", "pfd_moments", "gauss", "continuity")
_STEP_BP_RE = re.compile(r"^(.+?)\.\d+\.bp$")


def _get_path(data_dir: Path, prefix: str, step: int) -> Path:
    return data_dir / f"{prefix}.{step:09}.bp"


def _decode_psc(ds):
    return pscpy.decode_psc(ds, ["e", "i"])


@loader
class FieldLoaderBp(Loader):
    @classmethod
    def discover_prefixes(cls, data_dir: Path) -> list[str]:
        present = {m.group(1) for entry in data_dir.iterdir() if (m := _STEP_BP_RE.match(entry.name))}
        return [p for p in _KNOWN_PREFIXES if p in present]

    @classmethod
    def suffix(cls):
        return "bp"

    def get_data(self, config: PscPlotConfig) -> Field:
        ds = xr.open_mfdataset(
            paths=[_get_path(config.data_dir, self.prefix, step) for step in file_util.get_available_steps(config.data_dir, self.prefix + ".", ".bp")],
            combine="nested",
            concat_dim="t",
            preprocess=_decode_psc,
            parallel=True,
        )

        data = {key: ds[key] for key in ds.data_vars}
        var_infos = {key: lookup(self.prefix, key) for key in ds.variables}

        field = Field(
            data,
            FieldMetadata(
                active_key=self.active_key,
                prefix=self.prefix,
                var_infos=var_infos,
            ),
        )

        if self.active_key is not None:
            field = derive_field_variable(field, self.active_key, self.prefix)

        return field
