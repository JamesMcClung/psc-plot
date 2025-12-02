import typing


class DataWithAttrs(typing.Protocol):
    """A data class with an `attrs` field. Note that pandas DataFrames and xarray DataArrays all satisfy this property, but dask DataFrames don't by default."""

    attrs: dict[str, typing.Any]
