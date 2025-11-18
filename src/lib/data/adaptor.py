from __future__ import annotations

import inspect
from abc import abstractmethod

from .compatability import ConsumesData, ProducesData


class Adaptor(ConsumesData, ProducesData):
    @abstractmethod
    def apply(self, data): ...

    def get_name_fragments(self) -> list[str]:
        return []

    def get_modified_var_name(self, dep_var_name: str) -> str:
        return dep_var_name

    def get_input_data_type(self) -> type:
        *_, data_param = inspect.signature(self.apply).parameters.values()
        return data_param.annotation

    def get_output_data_type(self) -> type:
        return inspect.signature(self.apply).return_annotation
