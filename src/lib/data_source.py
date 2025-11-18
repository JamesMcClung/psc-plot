import inspect
from abc import ABC, abstractmethod

from .adaptors.pipeline import Pipeline


class DataSource(ABC):
    @abstractmethod
    def get_data(self, steps: list[int]): ...

    def get_data_type(self) -> type:
        return inspect.signature(self.get_data).return_annotation

    @abstractmethod
    def get_file_prefix(self) -> str:
        """The prefix of the data files that ultimately source the fields, e.g. 'pfd'"""

    @abstractmethod
    def get_var_name(self) -> str:
        """The plain-text name of the original, dependent variable"""

    @abstractmethod
    def get_modified_var_name(self) -> str:
        """The latex-formatted name (including applied formulae) of the dependent variable"""

    @abstractmethod
    def get_name_fragments(self) -> list[str]:
        """An ordered list of name fragments representing how this field is loaded and transformed"""


class DataSourceWithPipeline(DataSource):
    def __init__(self, source: DataSource, pipeline: Pipeline):
        self.source = source
        self.pipeline = pipeline

        self._validate()

    def get_data(self, steps: list[int]):
        da = self.source.get_data(steps)
        da = self.pipeline.apply(da)
        return da

    def get_data_type(self) -> type:
        return self.pipeline.get_output_data_type()

    def get_file_prefix(self) -> str:
        return self.source.get_file_prefix()

    def get_var_name(self) -> str:
        return self.source.get_var_name()

    def get_modified_var_name(self) -> str:
        return self.pipeline.get_modified_var_name(self.source.get_modified_var_name())

    def get_name_fragments(self) -> list[str]:
        return self.source.get_name_fragments() + self.pipeline.get_name_fragments()

    def _validate(self):
        source_output = self.source.get_data_type()
        pipeline_input = self.pipeline.get_input_data_type()
        if issubclass(source_output, pipeline_input):
            return

        raise ValueError(f"source {self.source} emits type {source_output.__name__}, but feeds into pipeline {self.pipeline} which accepts {pipeline_input.__name__}")
