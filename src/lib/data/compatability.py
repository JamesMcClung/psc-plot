from abc import ABC, abstractmethod


class ConsumesData(ABC):
    @abstractmethod
    def get_input_data_type(self) -> type: ...


class ProducesData(ABC):
    @abstractmethod
    def get_output_data_type(self) -> type: ...


class DataError(Exception): ...


def ensure_type[Data](consumer_name: str, data: Data, *allowed_types: type):
    if not isinstance(data, allowed_types):
        names_of_types = ", ".join(f"{t.__module__}.{t.__name__}" for t in allowed_types)
        raise DataError(f"{consumer_name} accepts only the following types: [{names_of_types}], but received data of type {data.__class__.__module__}.{data.__class__}")


def are_compatible(producer: ProducesData, consumer: ConsumesData) -> bool:
    return issubclass(producer.get_output_data_type(), consumer.get_input_data_type())


def require_compatible(producer: ProducesData, consumer: ConsumesData):
    if not are_compatible(producer, consumer):
        output_type = producer.get_output_data_type()
        input_type = consumer.get_input_data_type()
        raise DataError(f"{producer} produces type {output_type.__module__}.{output_type.__name__}, but feeds into {consumer} which only accepts type {input_type.__module__}.{input_type.__name__}")
