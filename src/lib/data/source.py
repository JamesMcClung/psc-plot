import typing
from abc import ABC, abstractmethod
from pathlib import Path

from lib.data.data_with_attrs import DataWithAttrs

from .pipeline import Pipeline


class DataSource(ABC):
    @classmethod
    @abstractmethod
    def discover(cls, data_dir: Path) -> list[str]:
        """Return prefixes this loader can handle in data_dir."""

    @abstractmethod
    def get_data(self) -> DataWithAttrs: ...


class DataSourceWithPipeline(DataSource):
    @classmethod
    def discover(cls, data_dir: Path) -> list[str]:
        return []

    def __init__(self, source: DataSource, pipeline: Pipeline):
        self.source = source
        self.pipeline = pipeline

    def get_data(self) -> typing.Any:
        da = self.source.get_data()
        da = self.pipeline.apply(da)
        return da
