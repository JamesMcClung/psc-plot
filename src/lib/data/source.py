import typing
from abc import abstractmethod

from lib.data.data_with_attrs import DataWithAttrs

from .pipeline import Pipeline


class DataSource:
    @abstractmethod
    def get_data(self) -> DataWithAttrs: ...


class DataSourceWithPipeline(DataSource):
    def __init__(self, source: DataSource, pipeline: Pipeline):
        self.source = source
        self.pipeline = pipeline

    def get_data(self) -> typing.Any:
        da = self.source.get_data()
        da = self.pipeline.apply(da)
        return da
