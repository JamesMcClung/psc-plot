class DataError(Exception): ...


def ensure_type[Data](consumer_name: str, data: Data, *allowed_types: type):
    if not isinstance(data, allowed_types):
        names_of_types = ", ".join(f"{t.__module__}.{t.__name__}" for t in allowed_types)
        raise DataError(f"{consumer_name} accepts only the following types: [{names_of_types}], but received data of type {data.__class__.__module__}.{data.__class__.__name__}")
