import warnings
from dataclasses import replace

import dask
import dask.dataframe as dd
import numpy as np
import pandas as pd
import scipy.optimize
import xarray as xr

from lib.config import PscPlotConfig
from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import DataWithAttrs, Field, FieldMetadata, List
from lib.data.data_world import DataWorld
from lib.data.expression import EXPRESSION_PARSER, BoundEvaluator, evaluate, split_assignment, variable_names
from lib.file_util import split_prepath
from lib.latex import Latex
from lib.scale import LogScale
from lib.var_info import VarInfo

ARTIFICIAL_COORD_COUNT = 100
"""How many coords to evaluate a list fit's curve on, along a variable that has none."""


class Fit(WorldAdaptor):
    """Fits the active variable to an expression, replacing it with the fitted curve.

    Of the bare `names`, those the expression uses are coefficients, and the rest are
    dims along which to fit each value separately. Every other dim is pooled into one fit.
    The coefficients end up as coords of the curve, so they label the plot."""

    def __init__(self, names: list[str], assignment: str):
        self.names = names
        self.assignment = assignment

        tree = EXPRESSION_PARSER.parse(assignment)
        if any(tree.find_data("scoped_variable")):
            raise ValueError("--fit expressions can't use prepath::key names")
        self.new_key, self.expression = split_assignment(tree)

        used = variable_names(self.expression)
        self.coef_keys = [name for name in names if name in used]
        self.per_value_dims = [name for name in names if name not in used]
        self.independent_keys = sorted(used - set(self.coef_keys))

        if not self.coef_keys:
            raise ValueError(f"--fit needs at least one coefficient, i.e. a name used in '{assignment}'")
        if not self.independent_keys:
            raise ValueError(f"--fit expression '{assignment}' must use at least one variable besides the coefficients")

    def apply_world(self, world: DataWorld) -> DataWorld:
        data = world.require_active_data()
        if isinstance(data, List):
            data = self._fit_list(data, world.config)
        else:
            data = self._fit_field(data, world.config)
        return world.with_active(data=data)

    def get_name_fragments(self) -> list[str]:
        return [f'fit_{"_".join(self.names)}_"{self.assignment}"']

    def _model(self, x: np.ndarray, *params: float):
        """The expression as a fitter's model: `x` stacks the independent variables, or is the only one."""
        xs = [x] if len(self.independent_keys) == 1 else list(x)
        values = dict(zip(self.independent_keys, xs)) | dict(zip(self.coef_keys, params))
        return evaluate(BoundEvaluator(values), self.expression)

    def _check_per_value_dims(self, dims: list[str], kind: str):
        for key in self.per_value_dims:
            if key not in dims:
                raise ValueError(f"--fit: '{key}' isn't used in the expression, so it must be a dim to fit per value, but the {kind} has no coords for '{key}'")

    def _check_enough_points(self, counts: xr.DataArray):
        if (counts < len(self.coef_keys)).any():
            raise ValueError(f"--fit: some fits have fewer usable points ({int(counts.min())}) than coefficients ({len(self.coef_keys)})")

    def _warn_if_unconverged(self, coefs: dict[str, xr.DataArray]):
        if any(bool(coef.isnull().any()) for coef in coefs.values()):
            warnings.warn(f"--fit: some fits of '{self.assignment}' didn't converge; their coefficients are NaN")

    def _finish(self, data: DataWithAttrs, curve: xr.DataArray, coefs: dict[str, xr.DataArray], active_info: VarInfo, config: PscPlotConfig) -> Field:
        """Wrap the curve, with the coefficients as coords, as the active variable of a field."""
        curve = curve.assign_coords(coefs).rename(self.new_key)
        _, prefix = split_prepath(data.metadata.prepath)
        info = replace(active_info, key=self.new_key, display=Latex(""))
        coef_infos = {key: config.registry.lookup(prefix, key) for key in self.coef_keys}
        return data.assign(var_infos=data.metadata.var_infos | coef_infos).with_active(data=curve, key=self.new_key, info=info)

    def _fit_field(self, data: Field, config: PscPlotConfig) -> Field:
        active = data.require_active_subdata()
        dims = list(active.dims)
        for key in self.independent_keys:
            if key not in dims:
                raise ValueError(f"--fit on a field can only use its dims as variables; '{key}' isn't one (--scatter first to fit against a variable)")
        self._check_per_value_dims(dims, "field")
        for key in self.coef_keys:
            if key in dims:
                # the curve keeps every dim of the field, and can't also have a coefficient coord of the same name
                raise ValueError(f"--fit: coefficient '{key}' has the same name as a dim")

        fit_dims = {dim for key in self.independent_keys for dim in active[key].dims}
        pooled = [dim for dim in dims if dim not in fit_dims and dim not in self.per_value_dims]
        if dask.is_dask_collection(active):
            active = active.chunk({dim: -1 for dim in [*fit_dims, *pooled]})

        self._check_enough_points(active.notnull().sum([*fit_dims, *pooled]))

        result = active.curvefit(
            coords=[active[key] for key in self.independent_keys],
            func=self._model,
            reduce_dims=pooled,
            p0={key: 1 for key in self.coef_keys},
            param_names=self.coef_keys,
            skipna=True,
            errors="ignore",
        )
        coefs = {key: result.curvefit_coefficients.sel(param=key, drop=True) for key in self.coef_keys}
        self._warn_if_unconverged(coefs)

        values = {key: active[key] for key in self.independent_keys} | coefs
        curve = evaluate(BoundEvaluator(values), self.expression)
        curve = curve.broadcast_like(active).transpose(*dims)
        return self._finish(data, curve, coefs, data.active_info, config)

    def _fit_list(self, data: List, config: PscPlotConfig) -> Field:
        columns = data.dims
        for key in self.independent_keys:
            if key not in columns:
                raise ValueError(f"--fit: the list has no variable '{key}'")
        coordss = {dim: np.asarray(coords) for dim, coords in data.coordss().items() if dim in columns and np.ndim(coords) > 0}
        self._check_per_value_dims(list(coordss), "list")

        active_key = data.require_active_key()
        df = data.data[[active_key, *self.independent_keys, *self.per_value_dims]]
        if isinstance(df, dd.DataFrame):
            df = df.compute()

        per_value_coordss = [coordss[dim] for dim in self.per_value_dims]
        coef_arrays = np.full((len(self.coef_keys), *map(len, per_value_coordss)), np.nan)
        for index in np.ndindex(*map(len, per_value_coordss)):
            group = df
            for dim, coords, i in zip(self.per_value_dims, per_value_coordss, index):
                group = group[group[dim] == coords[i]]
            coef_arrays[(slice(None), *index)] = self._fit_rows(group.dropna(subset=[active_key, *self.independent_keys]), active_key)

        coefs = {key: xr.DataArray(arr, coords=dict(zip(self.per_value_dims, per_value_coordss)), dims=self.per_value_dims) for key, arr in zip(self.coef_keys, coef_arrays)}
        self._warn_if_unconverged(coefs)

        eval_coordss = {key: coordss[key] if key in coordss else self._artificial_coords(df[key], data.metadata.var_infos.get(key)) for key in self.independent_keys}
        values = {key: xr.DataArray(coords, coords={key: coords}, dims=key) for key, coords in eval_coordss.items()} | coefs
        curve = evaluate(BoundEvaluator(values), self.expression).transpose(*self.independent_keys, *self.per_value_dims)

        _, prefix = split_prepath(data.metadata.prepath)
        dim_infos = {key: data.metadata.var_infos.get(key) or config.registry.lookup(prefix, key) for key in curve.dims}
        field = Field({}, FieldMetadata.create_from(data.metadata, active_key=None, var_infos=data.metadata.var_infos | dim_infos))
        return self._finish(field, curve, coefs, data.active_info, config)

    def _fit_rows(self, rows: pd.DataFrame, active_key: str) -> np.ndarray:
        """Fit one group's rows; NaNs if it doesn't converge."""
        if len(rows) < len(self.coef_keys):
            raise ValueError(f"--fit: some fits have fewer usable points ({len(rows)}) than coefficients ({len(self.coef_keys)})")
        xs = [rows[key].to_numpy() for key in self.independent_keys]
        xdata = xs[0] if len(xs) == 1 else np.vstack(xs)
        try:
            params, _ = scipy.optimize.curve_fit(self._model, xdata, rows[active_key].to_numpy(), p0=[1.0] * len(self.coef_keys))
        except RuntimeError:
            return np.full(len(self.coef_keys), np.nan)
        return params

    @staticmethod
    def _artificial_coords(values: pd.Series, info: VarInfo | None) -> np.ndarray:
        """Coords spanning `values`, spaced to match its scale."""
        key = values.name
        lower, upper = float(values.min()), float(values.max())
        if info is not None and isinstance(info.scale, LogScale):
            if lower <= 0:
                raise ValueError(f"--fit: log-spaced coords for '{key}' need a positive range, but it spans [{lower}, {upper}]")
            return np.geomspace(lower, upper, ARTIFICIAL_COORD_COUNT)
        return np.linspace(lower, upper, ARTIFICIAL_COORD_COUNT)
