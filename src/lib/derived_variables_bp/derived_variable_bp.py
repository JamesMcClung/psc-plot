import typing

import xarray as xr


class DeriveBp(typing.Protocol):
    def __call__(self, *variables: xr.DataArray) -> xr.DataArray: ...


class DerivedVariableBp:
    def __init__(
        self,
        name: str,
        base_var_names: list[str],
        derive: DeriveBp,
    ):
        self.name = name
        self.base_var_names = base_var_names
        self.derive = derive

    def assign_to(self, ds: xr.Dataset):
        ds[self.name] = self.derive(*(ds[base_var_name] for base_var_name in self.base_var_names))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(({', '.join(self.base_var_names)}) -> {self.name}: {self.derive!r})"
