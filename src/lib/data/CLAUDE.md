# CLAUDE.md — `src/lib/data`

Detail on the data layer: the values that flow through the node graph, and the adaptors that transform them. The pipeline overview, the auto-registration mechanism, `var_infos`, and the derived-variable registries live in the repo-root `CLAUDE.md`.

## PlotTarget

`src/lib/data/plot_target.py`: a `PlotTarget[D, SD]` names one thing to draw — the `data` itself (a snapshot of the `DataWithAttrs` at the moment `Versus` ran, **not** a lookup key into `DataWorld.datas`), a `spatial_dims` (`SpatialDimsXY(x_dim, y_dim)` or `SpatialDimsRTheta(r_dim, theta_dim)`, both with `ndims` and `unpack()`), an optional `color_dim` and `time_dim`, and an `axes_loc: (col, row)` (1-based) selecting which subplot it lands in. `Versus.apply_world` is what constructs and appends targets (`-v … loc=i,j` sets `axes_loc`); multiple targets sharing an `axes_loc` are overlaid on one axes. Because the target captures the data, later adaptors in the pipeline don't retroactively affect already-appended targets — that's what makes `--copy x -i y=1 -v t --copy x -i y=-1 -v t` produce two independent curves.

## WorldAdaptor / Adaptor class hierarchy

`src/lib/data/adaptor.py`:
- `WorldAdaptor` (ABC) — single abstract `apply_world(world) -> DataWorld`. The shared node-graph interface for **both loaders and adaptors**. Adaptors that must touch the whole world (e.g. `Versus`, which reads `active_data` and appends a `PlotTarget`) override this directly.
- `Adaptor(WorldAdaptor)` — default `apply_world` = `world.with_active(data=self.apply(world.active_data))`. Override `apply_field`/`apply_list`; the unused one raises a friendly "use `--bin`/`--scatter`" error.
- `MetadataAdaptor(Adaptor)` — wraps `apply` to also modify the active variable's `VarInfo` in `var_infos` (used to derive axis labels/filenames). Override `get_modified_display_latex(metadata)` and/or `get_modified_unit_latex(metadata)`; both receive the current `metadata` so they can inspect e.g. `active_key` and `active_var_info`.
- `BareAdaptor(MetadataAdaptor)` — operates on the raw active variable (a single `xr.DataArray` for fields, a single `pd.Series`/`dd.Series` for lists) and doesn't touch metadata; override `apply_field_bare`/`apply_list_bare`.

## Data wrapper

`src/lib/data/data_with_attrs.py` defines `DataWithAttrs[Data, Subdata, MD]` and concrete `Field` (whole = `dict[str, xr.DataArray]`, sub = `xr.DataArray`), `FullList` (pandas) and `LazyList` (dask) (whole = `DataFrame`, sub = `Series`). The **whole/sub distinction is what the three type params encode** — `data` is the container, `__getitem__(key)` yields one subdata, `dims` lists the keys.

Frozen dataclasses; mutate via `assign(data=None, /, **metadata_vals)` (replaces data and/or metadata fields in one call), `with_info(key, info)`, or `with_active(*, data=, key=, info=)` — the latter is the workhorse: it writes the subdata into `data[key]`, updates `var_infos[key]`, and sets `active_key`, any subset of which may be omitted. Read the active variable via `active_key` / `active_subdata` / `active_info` (all `None`-tolerant) or `require_active_key()` / `require_active_subdata()` (raise a friendly error). Most code should use these rather than `data` directly; `BareAdaptor` handles it automatically via the shims in `adaptor.py`.

Two more abstract accessors both subclasses implement: `coordss(key=None) -> dict[DimKey, Coords]` (for `Field`, read off the xarray coords; for `List`, the explicit `ListMetadata.coordss`) and `bounds(key=None) -> Bounds` (defaults to the active key; **coordinates win over data values**, and the upper bound is extended by one cell width so it works as an image extent — falls back to a dask-computed min/max otherwise). `dask_collections()` returns the underlying dask objects, used by `--dask-graph`.

Type aliases live in `src/lib/data/types.py`: `DimKey` / `SubdataKey` / `VarKey` (all `str`, but they document intent), `SpeciesKey`, `Bounds`, `Coords`.

`Metadata` carries `prepath` (e.g. `"run5/pfd_moments"`), `active_key` (`SubdataKey | None`), `var_infos` (`dict[VarKey, VarInfo]` — maps all known variable/dimension keys), and `species`. `active_key` defaults to `None` — particle data may have no active variable (e.g. pure scatter of positions); `active_var_info` raises if so. `var_infos` is populated at load time from `src/lib/var_info_registry.py` via `lookup(prefix, key)` for every coordinate and the active variable. `FieldMetadata` adds nothing (it's a marker subclass). `ListMetadata` adds `coordss`, `weight_key`, and `subject: Latex | None` — what the list contains (e.g. "Particles", "Ions", "Electrons"); set by the particle loaders, refined by `SpeciesFilter`, used by `Bin` (distribution-function subscripts) and `ScatterRenderer` (titles). `ListMetadata` also carries optional `partition_dim: str | None` and `partition_ranges: list[tuple[int,int]] | None` — when set (currently by both particle loaders, with `partition_dim="t"`), they let `Idx.apply_list` prune by `df.partitions[...]` instead of a `df[df[dim] == pos]` predicate filter, and they let `Bin` histogram one step at a time (see **Binning particle data** below). **Loader invariant:** `partition_ranges` must describe the actual partition layout of the `dd.DataFrame` returned (one entry per value of `partition_dim`, each `(start, end)` matching the per-step `npartitions`). Anything that changes that layout must keep them true: `Idx` rebases the surviving ranges onto the pruned frame, and clears both fields for an int index, which collapses the dim to a single value. `LazyList.compute()` clears them too, because they describe the dask layout and become meaningless after materialization. The unusual `**` unpacking via `__getitem__` + `keys()` is what `Metadata.create_from` and `assign` use to round-trip values between subclasses (`FieldMetadata` vs `ListMetadata`).

> **Note (split-vars):** the `spatial_dims` / `time_dim` / `color_dim` axis-selection fields and the `name_fragments` that `Metadata` used to carry have moved out — geometry/axis selection now lives on `PlotTarget` (inside `DataWorld`), and `name_fragments` are accumulated by the node graph (`DataProcessingNode.name_fragments` / `HasNameFragments`).

## Binning particle data

`Bin.apply_list` (`src/lib/data/adaptors/bin.py`) turns a `List` into a `Field` — it is the pipeline's **aggregate-to-plot-grid boundary**, and two non-obvious properties hold there.

**It does not pass `partition_dim` to `dask.array.histogramdd`.** That function allocates one *dense* `prod(nbins)` array **per dataframe partition** and sums them (`stacked_chunks = ((1,) * n_chunks, *all_nbins)`). Since partitions are laid out along `t` — each holds exactly one timestep — including `t` in the histogram made every partition allocate the whole `y × uy × t` grid in order to write one `t` slice of it, so peak memory scaled with `total bins × partitions in flight` and was **independent of particle count**. `--bin y=512 uy=256` over 201 steps meant 100 MiB per partition and died with numpy's `_ArrayMemoryError` on real runs. `_histogram_per_step` instead histograms each step over the remaining dims and stacks the results along `t` (`_step_bin_indices` maps steps onto `t` bins, so an explicit `--bin t=<n>` still works). Two things there are load-bearing: convert each column to a dask array **once** (every `to_dask_array()` call re-optimizes the whole dataframe expression, so calling it per step is O(n_steps²)), and select a step's partitions with a `.blocks` slice, which needs no per-partition row counts.

**It materializes the grid eagerly** (`self.materialize`). Downstream, the binned `Field` is plot-sized, but it used to stay lazy — so `bounds()` and *every animation frame* re-read the particle files: ~203 full passes for a 201-frame run. `--dask-graph` is the one consumer that wants the lazy graph, and `compile_action_nodes` clears the flag for it.

A dim whose coord has collapsed to a scalar (via `--idx t=<int>`) holds one value for every row, so it is dropped from the bin dims and carried through as a scalar coord of the result — which is also what the renderers key on to label it.

`tests/test_bin.py` guards all of this structurally (per-partition bin shape, one histogram pass per partition); `tests/test_memory.py` guards the peak-RSS scaling end-to-end, using a negligible particle count over many steps, since that is what makes the cluster failure reproducible on a laptop.

### Idea, not implemented: sparse binning via groupby

An alternative to the dense-histogram-plus-stacking above, recorded because the trade-off is not obvious and the crossover has never been measured. Instead of each partition allocating the output grid, each row gets one flat bin index and the aggregation is sparse:

```python
idx = np.ravel_multi_index([np.searchsorted(edges, col) - 1 for col, edges in ...], nbins)
counts = df.assign(_bin=idx).groupby("_bin")[weight_key].sum()  # dask, tree-reduced
out = np.zeros(nbins).ravel()
out[counts.index] = counts.values  # once, at the end
```

The two approaches have orthogonal per-partition costs: dense is `prod(nbins) × itemsize` regardless of row count, sparse is `min(rows, occupied bins) × ~12 bytes` regardless of bin count. At a 1M-row chunk, sparse costs ~12 MiB per partition, so it **loses** for `--bin y=512 uy=256` (0.5 MiB dense after the t stacking) and **wins** around and above ~3M bins — i.e. three or more large non-`t` bin dims, e.g. `--bin t= y=512 uy=256 uz=256` at 134 MiB dense. That is the remaining exposure to the failure mode the t stacking fixed.

Pros beyond the memory number:
- Peak memory becomes a function of `PSC_PLOT_DASK_CHUNK_SIZE`, a knob, instead of a function of the plot's resolution, which is not. Better cluster failure mode: turn the chunk size down rather than "this plot is impossible".
- It subsumes the per-step stacking entirely — fold `t` into the flat index and `_histogram_per_step`, `partition_dim`, `partition_ranges`, `_step_bin_indices` and `Idx`'s rebasing of the ranges all become unnecessary. One code path instead of two plus a metadata contract.

Cons:
- A groupby is a shuffle; even tree-reduced with `split_out=1`, the combine steps concatenate several partitions' pairs before aggregating, and it is meaningfully slower than `np.histogramdd`'s C loop on small grids.
- Non-uniform edges need a `searchsorted` per dim per partition, and out-of-range rows need dropping explicitly — both free in dense `histogramdd`.
- Picking per call by `prod(nbins)` means keeping both paths plus a crossover rule, which forfeits the simplification above. Deleting the dense path instead buys the simplification at the cost of the slowdown everywhere.

The open question that decides between one path and two: is the groupby within ~2x of `histogramdd` at ~131k bins? Unmeasured.
