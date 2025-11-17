from __future__ import annotations

import abc
import inspect


class Adaptor[Input, Output = Input](abc.ABC):
    @abc.abstractmethod
    def apply(self, data: Input) -> Output: ...

    def get_name_fragments(self) -> list[str]:
        return []

    def get_modified_var_name(self, dep_var_name: str) -> str:
        return dep_var_name

    @classmethod
    def get_input_data_type(cls) -> type[Input]:
        *_, data_param = inspect.signature(cls.apply).parameters.values()
        return data_param.annotation

    @classmethod
    def get_output_data_type(cls) -> type[Output]:
        return inspect.signature(cls.apply).return_annotation

    @staticmethod
    def are_compatible(adaptor1: Adaptor, adaptor2: Adaptor) -> bool:
        return issubclass(adaptor1.get_output_data_type(), adaptor2.get_input_data_type())
