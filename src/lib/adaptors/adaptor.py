import abc
import inspect


class Adaptor[Data](abc.ABC):
    @abc.abstractmethod
    def apply(self, data: Data) -> Data: ...

    def get_name_fragments(self) -> list[str]:
        return []

    def get_modified_var_name(self, dep_var_name: str) -> str:
        return dep_var_name

    @classmethod
    def get_data_type(cls) -> type[Data]:
        *_, data_param = inspect.signature(cls.apply).parameters.values()
        return data_param.annotation
