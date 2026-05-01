from abc import abstractmethod
from pathlib import Path

from lib.data.data_source import DataSource


class Loader(DataSource):
    @classmethod
    @abstractmethod
    def discover_prefixes(cls, data_dir: Path) -> list[str]:
        """Return prefixes this loader can handle in data_dir."""
