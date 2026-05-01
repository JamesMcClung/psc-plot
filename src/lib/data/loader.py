import warnings
from abc import abstractmethod
from pathlib import Path

from lib.data.data_source import DataSource
from lib.file_util import get_available_steps

LOADERS: list[type[Loader]] = []


class Loader(DataSource):
    @classmethod
    @abstractmethod
    def discover_prefixes(cls, data_dir: Path) -> list[str]:
        """Return prefixes this loader can handle in data_dir."""

    @classmethod
    @abstractmethod
    def suffix(cls) -> str:
        """Return the suffix that this loader supports."""

    def __init__(self, prefix: str, active_key: str | None = None):
        self.prefix = prefix
        self.steps = get_available_steps(prefix + ".", "." + self.suffix())
        self.active_key = active_key

    def _get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.active_key is not None:
            fragments.append(self.active_key)
        return fragments


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
