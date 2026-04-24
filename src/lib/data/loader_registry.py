from lib.data.source import DataSource

LOADERS: dict[str, type[DataSource]] = {}


def register_loader(prefix: str, cls: type[DataSource]) -> None:
    """Imperatively register a loader class under the given prefix. Overwrites
    any existing registration for that prefix."""
    LOADERS[prefix] = cls


def loader(*prefixes: str):
    def decorator[T: type[DataSource]](cls: T) -> T:
        for p in prefixes:
            register_loader(p, cls)
        return cls

    return decorator
