from lib.data.source import DataSource

LOADERS: dict[str, type[DataSource]] = {}


def loader(*prefixes: str):
    def decorator[T: type[DataSource]](cls: T) -> T:
        for p in prefixes:
            LOADERS[p] = cls
        return cls

    return decorator
