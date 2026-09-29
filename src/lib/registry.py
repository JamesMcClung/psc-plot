"""Variable display info and derived-variable pipelines, loaded from a directory of YAML files.

`shared.yml` holds entries shared by every prefix (prefix `None`, e.g. the x/y/z/t dims); every other `<prefix>.yml` holds that prefix's entries. See `src/lib/default_registries/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import yaml

from lib.latex import Latex
from lib.var_info import Geometry, VarInfo

if TYPE_CHECKING:
    from lib.data.adaptor import WorldAdaptor

SHARED_FILE_STEM = "shared"
_FIELDS = ("display", "unit", "geometry", "pipeline")
_GEOMETRIES: tuple[str, ...] = Geometry.__value__.__args__
# what YAML's double-quoted escapes (\a \b \t \n \v \f \r \e) produce
_CONTROL_CHARS = "\a\b\t\n\v\f\r\x1b"


class RegistryError(ValueError): ...


@dataclass(frozen=True)
class RegistryEntry:
    var_info: VarInfo
    pipeline: list[WorldAdaptor] | None = None


def _normalize_prefix(prefix: str | None) -> str | None:
    # ADIOS2 particle files are prefixed per species (prt.e, prt.i) but share one registry file
    if prefix is not None and prefix.startswith("prt."):
        return "prt"
    return prefix


class _UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that rejects duplicate mapping keys instead of silently keeping the last."""


def _construct_mapping_rejecting_duplicates(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise RegistryError(f"duplicate key '{key}' (line {key_node.start_mark.line + 1})")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_rejecting_duplicates)


def _read_yaml(path: Path) -> dict:
    try:
        with path.open() as f:
            content = yaml.load(f, Loader=_UniqueKeyLoader)
    except (yaml.YAMLError, RegistryError) as e:
        raise RegistryError(f"{path.name}: {e}") from e

    if content is None:
        return {}
    if not isinstance(content, dict):
        raise RegistryError(f"{path.name}: expected a mapping of variable keys to entries")
    return content


def _check_latex(where: str, name: str, value: object) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{where}: '{name}' must be a string")
    if any(char in value for char in _CONTROL_CHARS):
        raise RegistryError(f"{where}: '{name}' contains a control character; write LaTeX in single quotes (e.g. '\\text{{e}}'), since double-quoted YAML turns '\\t' into a tab")
    return value


def _parse_entry(path: Path, prefix: str | None, key: object, raw: object, parse_steps: Callable[[list[str]], list[WorldAdaptor]]) -> RegistryEntry:
    if not isinstance(key, str):
        raise RegistryError(f"{path.name}: key {key!r} must be a string; quote it (YAML reads e.g. on/off/yes/no as booleans)")
    where = f"{path.name}: {key}"

    if not isinstance(raw, dict):
        raise RegistryError(f"{where}: expected a mapping with at least 'display'")
    if unknown := sorted(set(raw) - set(_FIELDS)):
        raise RegistryError(f"{where}: unknown field(s) {unknown}; expected some of {list(_FIELDS)}")
    if "display" not in raw:
        raise RegistryError(f"{where}: missing 'display'")

    display = _check_latex(where, "display", raw["display"])
    unit = _check_latex(where, "unit", raw.get("unit", ""))

    geometry = raw.get("geometry")
    if geometry is not None and geometry not in _GEOMETRIES:
        raise RegistryError(f"{where}: geometry {geometry!r} is not one of {list(_GEOMETRIES)}")

    pipeline = None
    if "pipeline" in raw:
        raw_pipeline = raw["pipeline"]
        if not isinstance(raw_pipeline, list) or not all(isinstance(step, str) for step in raw_pipeline):
            raise RegistryError(f"{where}: 'pipeline' must be a list of strings, one CLI step each")
        if prefix is None:
            raise RegistryError(f"{where}: entries in {SHARED_FILE_STEM}.yml cannot have a pipeline")
        try:
            pipeline = parse_steps(raw_pipeline)
        except ValueError as e:
            raise RegistryError(f"{where}: {e}") from e

    return RegistryEntry(VarInfo(Latex(display), Latex(unit), geometry, key=key), pipeline)


class Registry:
    def __init__(self, entries: dict[tuple[str | None, str], RegistryEntry]):
        self._entries = entries

    @classmethod
    def load(cls, registries_dir: Path) -> Registry:
        if not registries_dir.exists():
            raise RegistryError(f"registries directory {registries_dir} does not exist")
        if not registries_dir.is_dir():
            raise RegistryError(f"registries directory {registries_dir} is not a directory")

        # Deferred: the parser imports every adaptor, and several adaptors reach the registry via config.
        from lib.parsing.parse import parse_steps

        entries: dict[tuple[str | None, str], RegistryEntry] = {}
        for path in sorted(registries_dir.glob("*.yml")):
            prefix = None if path.stem == SHARED_FILE_STEM else path.stem
            for key, raw in _read_yaml(path).items():
                entries[(prefix, key)] = _parse_entry(path, prefix, key, raw, parse_steps)
        return cls(entries)

    def entry(self, prefix: str | None, key: str) -> RegistryEntry | None:
        return self._entries.get((_normalize_prefix(prefix), key))

    def lookup(self, prefix: str | None, key: str) -> VarInfo:
        """Look up display/unit info for a key: the prefix's entry, then the shared entry, then a bare fallback."""
        for candidate_prefix in (prefix, None):
            if entry := self.entry(candidate_prefix, key):
                return entry.var_info

        return VarInfo(Latex(key), Latex(""), key=key)

    def pipeline(self, prefix: str, key: str) -> list[WorldAdaptor] | None:
        entry = self.entry(prefix, key)
        return entry.pipeline if entry else None

    def derivable_keys(self, prefix: str) -> list[str]:
        prefix = _normalize_prefix(prefix)
        return [key for (entry_prefix, key), entry in self._entries.items() if entry_prefix == prefix and entry.pipeline is not None]
