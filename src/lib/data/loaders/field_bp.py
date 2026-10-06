import re
from pathlib import Path

import xarray as xr

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.data_with_attrs import Field, FieldMetadata
from lib.data.loader import Loader, loader

_KNOWN_PREFIXES = ("pfd", "pfd_moments", "gauss", "continuity")
_STEP_BP_RE = re.compile(r"^(.+?)\.\d+\.bp$")


def _get_path(data_dir: Path, prefix: str, step: int) -> Path:
    return data_dir / f"{prefix}.{step:09}.bp"


def _decode_psc(ds: xr.Dataset):
    if "time" in ds.variables or "time" in ds.dims:
        ds = ds.rename(time="t")
    for key, corner in zip(["x", "y", "z"], ds.attrs["corner"]):
        ds.coords[key] = ds.coords[key] - (ds.coords[key][0] - corner)
    return ds


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
            paths=[_get_path(config.data_root / self.subdir, self.prefix, step) for step in file_util.get_available_steps(config.data_root / self.subdir, self.prefix + ".", ".bp")],
            preprocess=_decode_psc,
            parallel=True,
        )

        data = {key: ds[key] for key in ds.data_vars}
        var_infos = {key: config.registry.lookup(self.prefix, key) for key in ds.variables}

        return Field(
            data,
            FieldMetadata(
                prepath=self.prepath,
                var_infos=var_infos,
            ),
        )
