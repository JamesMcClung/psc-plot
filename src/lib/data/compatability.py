from abc import ABC, abstractmethod


class ConsumesData(ABC):
    @abstractmethod
    def get_input_data_type(self) -> type: ...


class ProducesData(ABC):
    @abstractmethod
    def get_output_data_type(self) -> type: ...


class DataError(Exception): ...


def are_compatible(producer: ProducesData, consumer: ConsumesData) -> bool:
    return issubclass(producer.get_output_data_type(), consumer.get_input_data_type())


def require_compatible(producer: ProducesData, consumer: ConsumesData):
    if not are_compatible(producer, consumer):
        raise DataError(f"{producer} produces type {producer.get_output_data_type().__name__}, but feeds into {consumer} which only accepts type {consumer.get_input_data_type().__name__}")
