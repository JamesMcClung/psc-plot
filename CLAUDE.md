# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`psc-plot` is a CLI tool for visualizing simulation output from PSC (Plasma Simulation Code). It loads field and particle data files from a directory, applies a configurable pipeline of transformations, and renders 1D/2D static or animated plots (matplotlib) optionally saved as images or videos via ffmpeg.

## Running

Install in editable mode (one-time):

```sh
pip install -e .
```

Then invoke as:

```sh
psc-plot <prefix> [variable] [options]
```

Or directly via `py src/main.py <prefix> [variable] [options]` (backward-compatible).

Where `<prefix>` selects the data source: field prefixes (`pfd`, `pfd_moments`, `gauss`, `continuity`) or particle prefixes (`prt`). Examples live in `plots/check.sh` and `plots/check2.sh` and serve as the de-facto smoke tests / usage reference.

Common flags:
- `-q` quiet (don't show interactively), `-s [dir]` save output (defaults to `.` if dir omitted)
- Adaptor flags such as `--roll`, `--reduce`, `--bin`, `--scatter [name]`, `--mag`, `--nan0`, `--scale`, `--fourier`/`-f`, `--pos`, `--species`, `--transform-spherical`, `-v` (versus, sets axes), `-b` (bin)

Required environment (see `src/lib/config.py`):
- `PSC_PLOT_DATA_DIR` — directory containing the data files (must be set; `set_data_dir.sh <dir>` is a convenience script that exports it)
- `PSC_PLOT_FFMPEG_BIN` — optional, falls back to `which ffmpeg`; needed for saving animations
- `PSC_PLOT_DASK_NUM_WORKERS` — optional, defaults to `os.cpu_count()`
- `PSC_PLOT_DASK_CHUNK_SIZE` — optional, rows per dask partition for particle loads (default 1_000_000); reduce to bound peak memory on large files
- `PSC_PLOT_DASK_SCHEDULER` — optional; if set to `"processes"`, uses dask's processes scheduler; if `"distributed"`, spins up a `dask.distributed.LocalCluster` with `n_workers=dask_num_workers, threads_per_worker=1, processes=True`. Unset = dask default (threads).

`PSC_PLOT_DATA_DIR` is read at module-import time (`CONFIG = PscPlotConfig._load()` in `src/lib/config.py`), so it must be set in the environment before any `lib.*` import. In tests, `tests/conftest.py` sets it before importing `lib`.

Inspect data files directly with `bpls <file.bp>` (ADIOS2) and `h5ls <file.h5>` (HDF5); pass `-l` to `bpls` or `-r` to `h5ls` for more detail.

Use `.venv/bin/pytest`, `.venv/bin/pip`, etc. — system Python is 3.10 and can't install this package (requires 3.13+).

Package management is via `pyproject.toml` (setuptools backend).

## Testing

Install test dependencies:

```sh
pip install -e ".[test]"
```

Run the figure consistency tests:

```sh
pytest --mpl
```

Tests live in `tests/test_plots.py` and use `pytest-mpl` for image comparison against baseline PNGs in `tests/baseline/`. Each test runs the full CLI pipeline (parsing → loading → adaptors → plotting) against small test datasets in `tests/data/` (test-2d: x=1,y=8,z=16; test-3d: x=4,y=4,z=4).

To regenerate baselines after intentional visual changes:

```sh
pytest --mpl-generate-path=tests/baseline
```

The test helper `make_plot()` in `tests/conftest.py` parses CLI args, runs the pipeline, and returns the initialized matplotlib Figure. Tests can switch data directories via `data_dir="test-3d"`.

New `@pytest.mark.mpl_image_compare` tests must pass `style="default"` — without it, fonts and interpolation render incorrectly. The `MPL_KWARGS` dict in `tests/test_plots.py` already bundles this.

Running `plots/check*.sh` against a real data directory remains useful for manual validation of more complex scenarios.

## Formatting

Code is formatted with [Ruff](https://docs.astral.sh/ruff/) and import-sorted via Ruff's isort rule. CI enforces both via `.github/workflows/format.yml`.

Install dev tooling:

```sh
pip install -e ".[dev]"
```

Run locally:

```sh
ruff format .
ruff check --fix .
```

Conventions:

- `line-length` is set to 320 (Ruff's maximum) — effectively unlimited for this codebase. Ruff respects the "magic trailing comma": a trailing comma in a call/collection forces it to stay multi-line; without one, it collapses onto a single line if it fits. Use a trailing comma to signal "I want this exploded."
- Only the isort rule (`I`) is enabled. No other lint rules.

VS Code: install the official Ruff extension (`charliermarsh.ruff`) and add to your settings to format and organize imports on save:

```json
"[python]": {
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  }
}
```

`.vscode/settings.json` is intentionally not checked in.

## Architecture

The code lives under `src/lib/` and is organized around **loaders** (sources), **adaptors** (transforms), and **plots** (renderers). A lazy **node graph** wraps a **`DataWorld`** value that flows through them; argument parsing wires it all together.

### Data flow

1. `cli.main()` (`src/lib/cli.py`) configures dask, calls `parse_args()` (`src/lib/parsing/parse.py`) — a flat argparse parser with positional `prefix` + optional `variable` plus all registered adaptor/hook flags, returning an `Args` namespace (`src/lib/parsing/args.py`). It then calls `compile_action_nodes(args, config)` (`src/lib/data/compile.py`) and `.pull()`s each returned action node. (The `prefix` positional is **not** choices-constrained; an unknown prefix fails later in `get_loader`.)
2. Everything runs through a lazy, memoized **node graph** (`src/lib/data/node.py`). `compile_action_nodes` chains: `RootNode(config)` → `AdaptorNode(loader)` → one `AdaptorNode` per user adaptor → `PlotNode(hooks)` → action node(s): `ShowPlotNode` (`--show`, default on), `SavePlotNode` (`--save`), and/or `DaskGraphNode` (`--dask-graph`, renders the dask graph as SVG instead of plotting). Each `DataProcessingNode` has a `@cache`d `pull()` and accumulates `name_fragments` (used to derive save filenames). If the adaptor list contains no `Versus`, a default `Versus(["y","z"], time_dim_rule="guess", color_dim=None)` is appended (`_with_versus`) — this is what selects axes/color/time dims and appends the plot target.
3. Data flows as a **`DataWorld`** (`src/lib/data/data_world.py`): a frozen dataclass holding `datas: dict[str, DataWithAttrs]`, an `active_key: str | None`, `plot_targets: list[PlotTarget]`, and `config`. `RootNode.pull()` returns an empty world; each `AdaptorNode` applies a `WorldAdaptor` to it. The **loader is itself a `WorldAdaptor`** (`Loader.apply_world` inserts the loaded `DataWithAttrs` under key = `prefix` and makes it active). `DataWorld.active_data` / `with_active_data()` operate on `datas[active_key]`. Holding **multiple named datas + multiple plot targets** is the "split vars" capability this branch is named for.
4. `PlotNode.pull()` calls `get_plot(world)` (`src/lib/plotting/get_plot.py`), which builds one `Renderer` **per `PlotTarget`**: `Field1dRenderer` when the target has no `color_dim`; `PolarFieldRenderer` / `Field2dRenderer` chosen by `SpatialDimsRTheta` / `SpatialDimsXY`; `ScatterRenderer` for `List` data with exactly 2 spatial dims. It wraps the renderer **list** in `StaticPlot` or `AnimatedPlot` based on `n_frames = max(r.get_n_frames())` — **animated iff `n_frames > 1`**, not on `time_dim` presence. Hooks are then attached via `plot.add_hook()`.
5. `ShowPlotNode`/`SavePlotNode.pull()` call `plot.show()` / `plot.save_to_path()`, which lazily `_initialize()` the figure (see the PlotInfo/AxesManager layer below).

### PlotTarget

`src/lib/data/plot_target.py`: a `PlotTarget` names one thing to draw — a `prefix` (which entry of `DataWorld.datas`), a `spatial_dims` (`SpatialDimsXY(x_dim, y_dim)` or `SpatialDimsRTheta(r_dim, theta_dim)`), an optional `color_dim` and `time_dim`, and an `axes_index: (col, row)` (1-based) selecting which subplot it lands in. `Versus.apply_world` is what constructs and appends targets; multiple targets sharing an `axes_index` are overlaid on one axes.

### WorldAdaptor / Adaptor class hierarchy

`src/lib/data/adaptor.py`:
- `WorldAdaptor` (ABC) — single abstract `apply_world(world) -> DataWorld`. The shared node-graph interface for **both loaders and adaptors**. Adaptors that must touch the whole world (e.g. `Versus`, which reads `active_data` and appends a `PlotTarget`) override this directly.
- `Adaptor(WorldAdaptor)` — default `apply_world` = `world.with_active_data(self.apply(world.active_data))`. Override `apply_field`/`apply_list`; the unused one raises a friendly "use `--bin`/`--scatter`" error.
- `MetadataAdaptor(Adaptor)` — wraps `apply` to also modify the active variable's `VarInfo` in `var_infos` (used to derive axis labels/filenames). Override `get_modified_display_latex(metadata)` and/or `get_modified_unit_latex(metadata)`; both receive the current `metadata` so they can inspect e.g. `active_key` and `active_var_info`.
- `BareAdaptor(MetadataAdaptor)` — operates on the raw active variable (a single `xr.DataArray` for fields, a single `pd.Series`/`dd.Series` for lists) and doesn't touch metadata; override `apply_field_bare`/`apply_list_bare`.

### Auto-registration of loaders, adaptors, and hooks

`src/lib/__init__.py` imports `lib.data.loaders`, `lib.data.adaptors`, and `lib.plotting.hooks`, whose `__init__.py` files glob and `importlib.import_module` every sibling `*.py`.

**Loaders** (`src/lib/data/loaders/`) are `Loader` (a `WorldAdaptor` subclass) classes registered via the bare `@loader` decorator from `src/lib/data/loader.py`, which appends to `LOADERS: list[type[Loader]]`. Each loader exposes `discover_prefixes(cls, data_dir: Path) -> list[str]` and `suffix(cls)` classmethods, plus `get_data(config) -> DataWithAttrs`.

`discover_loaders(data_dir)` polls every registered loader's `discover_prefixes()` and returns a `dict[str, type[Loader]]`; `get_loader(data_dir, prefix, active_key)` instantiates the one matching `prefix`. On prefix conflicts, the later-registered loader wins with a `UserWarning`, so user-defined loaders can shadow built-ins. To add a new data source, drop a file into `src/lib/data/loaders/`, decorate the class with `@loader`, and implement `discover_prefixes`/`suffix`/`get_data`.

**Adaptors and hooks** register their argparse flags via the `@arg_parser(...)` / `@const_arg(...)` decorators in `src/lib/parsing/args_registry.py`, which append to the module-level `CUSTOM_ARGS` list. `parse._get_parser()` then iterates `CUSTOM_ARGS` and adds them to the parser. To add a new adaptor or hook, drop a new file into `src/lib/data/adaptors/` (or `src/lib/plotting/hooks/`) and decorate its parse function.

**Consequence:** a loader, adaptor, or hook that fails to register (e.g. import error in that file) will silently disappear from the CLI; suspect the auto-import if a flag or prefix goes missing.

### Data wrapper

`src/lib/data/data_with_attrs.py` defines `DataWithAttrs[D, MD]` and concrete `Field` (dict of `xr.DataArray`), `FullList` (pandas), `LazyList` (dask). Frozen dataclasses; mutate via `assign_data` / `assign_metadata` / `assign`. `Metadata` now carries only `active_key` (`str | None`) and `var_infos` (`dict[str, VarInfo]` — maps all known variable/dimension keys to `VarInfo` objects). `active_key` defaults to `None` — particle data may have no active variable (e.g. pure scatter of positions). The convenience property `active_var_info` returns `var_infos[active_key]`. `var_infos` is populated at load time from `src/lib/var_info_registry.py` via `lookup(prefix, key)` for every coordinate and the active variable. `FieldMetadata` also carries `prefix` (the file prefix, e.g. `"pfd_moments"`). `ListMetadata` also carries `subject: Latex | None` — describes what the list contains (e.g. "Particles", "Ions", "Electrons"); set by `ParticleLoader`, refined by `SpeciesFilter`, and used by `Bin` (for distribution function subscripts) and `ScatterRenderer` (for plot titles). `ListMetadata` also carries optional `partition_dim: str | None` and `partition_ranges: list[tuple[int,int]] | None` — when set (currently by both particle loaders, with `partition_dim="t"`), they let `Idx.apply_list` prune by `df.partitions[...]` instead of a `df[df[dim] == pos]` predicate filter. **Loader invariant:** `partition_ranges` must describe the actual partition layout of the `dd.DataFrame` returned (one entry per value of `partition_dim`, each `(start, end)` matching the per-step `npartitions`). `LazyList.compute()` clears these fields because they describe the dask layout and become meaningless after materialization. The unusual `**` unpacking via `__getitem__` + `keys()` is what `Metadata.create_from` and `assign` use to round-trip values between subclasses (`FieldMetadata` vs `ListMetadata`).

> **Note (split-vars):** the `spatial_dims` / `time_dim` / `color_dim` axis-selection fields and the `name_fragments` that `Metadata` used to carry have moved out — geometry/axis selection now lives on `PlotTarget` (inside `DataWorld`), and `name_fragments` are accumulated by the node graph (`DataProcessingNode.name_fragments` / `HasNameFragments`).

Both `Field` and `List` expose an `active_data` property and `with_active_data()` method. For `Field`, `active_data` returns the `xr.DataArray` for `metadata.active_key`; `with_active_data(da)` replaces it and drops grid-incompatible siblings. For `List`, `active_data` returns the `pd.Series`/`dd.Series` column for `metadata.active_key`; `with_active_data(series)` replaces that column. Both raise `ValueError` if `active_key` is `None`. Most code should use `active_data` rather than `data` directly. `BareAdaptor` handles this automatically via the shims in `adaptor.py`.

The class-level `data: ...`/`metadata: ...` annotations on the subclasses look redundant but are intentional — see the comment in `DataWithAttrs.__init__`. They are needed so `isinstance`-narrowed code gets the concrete types; don't "clean them up."

### PlotInfo, renderers, and AxesManager

Renderers don't draw to matplotlib directly — they produce a `PlotInfo` (`src/lib/plotting/plot_info.py`: `LineInfo` / `ImageInfo` / `ScatterInfo` / `PolarMeshInfo`, all `PlotInfo`/`PlotInfo2D`) describing *what* to draw: data arrays, per-dim `dim_scales` / `dim_bounds` / `dim_displays` / `dim_units`, `scalar_coord_values` (for titles), `axes_index`, and `projection`. `Renderer.__init__` calls `init_plot_info()`; `update_plot_info(frame)` mutates the `PlotInfo` for animation via `PlotInfo.set(key, value)`, which fires registered `_setter_callbacks` that update the matplotlib artists in place.

`setup_fig(plot_infos)` (`src/lib/plotting/setup_fig.py`) is called once from `Plot._initialize()`. It groups infos by `axes_index` into a subplot grid, then picks an `AxesManager` per axes: single info → `AxesManagerSingleLine` / `…Image` / `…Scatter` / `…PolarMesh`; several `LineInfo`s → `AxesManagerMultiLine` (shared axes + legend); one `ImageInfo` + `LineInfo`s → `AxesManagerImageAndLines` (lines on a twinned y-axis). Each manager wires `PlotInfo._setter_callbacks` so later `.set()` calls re-render without rebuilding the figure. Figures use `layout="constrained"`.

### Hooks

Hooks (`src/lib/plotting/hooks/`) such as `--grid`, `--vline`, `--fit`, `--show-com`, `--show-initial` subclass `Hook` (`src/lib/plotting/hook.py`) and implement `post_init_fig(message)` / `post_update_fig(message)`, receiving a `DrawMessage(plot_info, axes, frame_data)`. `PlotNode` attaches them and `Plot._initialize()` calls `post_init_fig` after building the figure. **Currently hooks are applied to the first renderer/axes only** — see the TODO in `plot.py`.

### Dimensions and var_infos

`src/lib/var_info.py` defines `VarInfo` as a frozen value (`display: Latex`, `unit: Latex`, `geometry`, `key`). `src/lib/var_info_registry.py` provides a single `_REGISTRY` dict keyed by `(prefix | None, key)` — `None`-prefix entries are shared dimensions (x, y, z, t); string-prefix entries are per-file-type variables (e.g. `("pfd", "hx_fc")` → `VarInfo(display="B_x", ...)`).
- `lookup(prefix, key)` — checks prefixed registry, then `None`-prefix registry, then Fourier toggle of the base key; falls back to a plain `VarInfo(display=key)`.

**Per-instance invariant:** `metadata.var_infos` is the single source of truth for axis labels, coord-value labels, and Fourier/transform geometry checks during the pipeline. Adaptors that rename, add, or remove a dimension key (Fourier, TransformPolar, TransformSpherical, etc.) MUST update `var_infos` accordingly inside `apply_field` / `apply_list`. The `MetadataAdaptor` hooks (`get_modified_display_latex`/`get_modified_unit_latex`) only see post-apply metadata and only target the active variable's `VarInfo`, so dim-key swaps must be handled in `apply` itself, not via the hooks.

### Derived variables

`src/lib/derived_field_variables/registry.py` and `derived_particle_variables/registry.py` register computed variables per file prefix using `@derived_field_variable("pfd_moments")` decorators. The decorated function's parameter names declare the dependencies (raw or other derived variables); the loader resolves and computes them on demand.

`--derive` works for both field and particle data. For fields, it operates on the underlying `xr.Dataset` and can reference any variable in the dataset or resolve names from the derived-variable registry (via `FieldMetadata.prefix`). It updates `metadata.active_key` to point to the newly created variable.

`Derive` (`src/lib/data/adaptors/derive.py`) is a `WorldAdaptor` (overrides `apply_world`), not a plain `Adaptor`, because expressions may reference variables scoped to **another prefix** via the `::` operator (the same operator `--with` uses), e.g. `--derive electron_power="jy_ec*pfd_moments::jy_e"`. Unscoped names resolve against the active field; `prefix::key` names resolve against `world.datas[prefix]`, auto-loading that prefix (via `get_loader(...)`, reusing it if already present) exactly as `--with` does. Both paths go through `_resolve_field_variable`, which pulls the key from the dataset or that prefix's derived-variable registry. Cross-prefix arrays are combined with xarray's default arithmetic alignment (no regridding). Scoped refs are **field-only** — a `prefix::key` in a particle/list derive raises a clear error. The Lark grammar's `variable` rule is `(CNAME "::")? CNAME`, so a scoped reference is a `variable` tree with two `CNAME` children.
