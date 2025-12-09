import typing
from abc import abstractmethod

from lib.data.data_with_attrs import DataWithAttrs

from .pipeline import Pipeline


class DataSource:
    @abstractmethod
    def get_data(self) -> DataWithAttrs: ...

    @abstractmethod
    def get_file_prefix(self) -> str:
        """The prefix of the data files that ultimately source the fields, e.g. 'pfd'"""

    @abstractmethod
    def get_var_name(self) -> str:
        """The plain-text name of the original, dependent variable"""

    @abstractmethod
    def get_name_fragments(self) -> list[str]:
        """An ordered list of name fragments representing how this field is loaded and transformed"""


class DataSourceWithPipeline(DataSource):
    def __init__(self, source: DataSource, pipeline: Pipeline):
        self.source = source
        self.pipeline = pipeline

    def get_data(self) -> typing.Any:
        da = self.source.get_data()
        da = self.pipeline.apply(da)
        return da

    def get_file_prefix(self) -> str:
        return self.source.get_file_prefix()

    def get_var_name(self) -> str:
        return self.source.get_var_name()

    def get_name_fragments(self) -> list[str]:
        return self.source.get_name_fragments() + self.pipeline.get_name_fragments()
