import warnings
from abc import abstractmethod
from pathlib import Path

from lib.config import PscPlotConfig
from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.file_util import Prepath, split_prepath


class Loader(WorldAdaptor):
    @classmethod
    @abstractmethod
    def discover_prefixes(cls, data_dir: Path) -> list[str]:
        """Return prefixes this loader can handle in data_dir."""

    @classmethod
    @abstractmethod
    def suffix(cls) -> str:
        """Return the suffix that this loader supports."""

    def __init__(self, prepath: Prepath):
        self.prepath = prepath
        self.subdir, self.prefix = split_prepath(prepath)

    def get_name_fragments(self) -> list[str]:
        return [self.prepath]

    def apply_world(self, world):
        return world.with_data(self.prepath, self.get_data(world.config))

    @abstractmethod
    def get_data(self, config: PscPlotConfig) -> DataWithAttrs: ...


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


def get_loader(data_root: Path, prepath: Prepath) -> Loader:
    subdir, prefix = split_prepath(prepath)
    loader_types = discover_loaders(data_root / subdir)
    return loader_types[prefix](prepath)


def load(config: PscPlotConfig, prepath: Prepath) -> DataWithAttrs:
    loader = get_loader(config.data_root, prepath)
    return loader.get_data(config)
