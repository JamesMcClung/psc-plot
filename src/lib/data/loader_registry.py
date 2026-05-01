import warnings
from pathlib import Path

from lib.data.data_source import Loader

LOADERS: list[type[Loader]] = []


def loader[T: type[Loader]](cls: T) -> T:
    """Register a loader class. Each loader's discover() classmethod determines
    which prefixes it claims for a given data dir."""
    LOADERS.append(cls)
    return cls


def discover_loaders(data_dir: Path) -> dict[str, type[Loader]]:
    """Poll every registered loader for the prefixes it claims in data_dir.
    On conflict, the later-registered loader wins (with a warning), so
    user-defined loaders can shadow built-ins."""
    result: dict[str, type[Loader]] = {}
    for cls in LOADERS:
        for prefix in cls.discover_prefixes(data_dir):
            if prefix in result:
                warnings.warn(
                    f"prefix '{prefix}' claimed by both {result[prefix].__name__} and {cls.__name__}; using {cls.__name__}",
                    UserWarning,
                    stacklevel=2,
                )
            result[prefix] = cls
    return result
