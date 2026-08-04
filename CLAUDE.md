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
psc-plot <prepath> [variable] [options]
```

Or directly via `py src/main.py <prepath> [variable] [options]` (backward-compatible).

Where `<prepath>` is a **path relative to `PSC_PLOT_DATA_DIR`, ending in the file prefix** — e.g. `pfd` (data root itself) or `run5/pfd` (subdirectory). The prefix part selects the data source: field prefixes (`pfd`, `pfd_moments`, `gauss`, `continuity`) or particle prefixes (`prt`). `Prepath` is just a `str` alias (`src/lib/file_util.py`); `split_prepath()` splits it into `(subdir, prefix)`. Examples live in `plots/check.sh` and `plots/check2.sh` and serve as the de-facto smoke tests / usage reference.

Common flags:
- `-q` quiet (don't show interactively), `-s [dir]` save output (defaults to `.` if dir omitted)
- `-w`/`--with [prepath::][var_key]` switch the active dataset and/or variable mid-pipeline (loads the prepath if not already in the world); `--copy [new=old|old]` duplicate a variable + its metadata; `-c`/`--compute` force full computation
- Adaptor flags such as `--roll`, `--reduce`, `--bin`, `--scatter [name]`, `--mag`, `--nan0`, `--scale`, `--fourier`/`-f`, `--pos`, `--species`, `--transform-spherical`, `-v` (versus, sets axes), `-b` (bin)

Required environment (see `src/lib/config.py`):
- `PSC_PLOT_DATA_DIR` — the data **root** directory (`config.data_root`; prepaths resolve against it). Defaults to the cwd if unset; `set_data_dir.sh <dir>` is a convenience script that exports it
- `PSC_PLOT_FFMPEG_BIN` — optional, falls back to `which ffmpeg`; needed for saving animations
- `PSC_PLOT_DASK_NUM_WORKERS` — optional, defaults to `os.cpu_count()`
- `PSC_PLOT_DASK_CHUNK_SIZE` — optional, rows per dask partition for particle loads (default 1_000_000); reduce to bound peak memory on large files
- `PSC_PLOT_DASK_SCHEDULER` — optional; if set to `"processes"`, uses dask's processes scheduler; if `"distributed"`, spins up a `dask.distributed.LocalCluster` with `n_workers=dask_num_workers, threads_per_worker=1, processes=True`. Unset = dask default (threads).

The environment is read **once, explicitly**, via `PscPlotConfig.from_env()` in `cli.main()`; the resulting `PscPlotConfig` is threaded through the node graph and lives on `DataWorld.config`. There is no module-level `CONFIG` singleton, so nothing depends on import order — tests construct `PscPlotConfig(data_root=...)` directly (see `CONFIG_2D` in `tests/conftest.py`).

Inspect data files directly with `bpls <file.bp>` (ADIOS2) and `h5ls <file.h5>` (HDF5); pass `-l` to `bpls` or `-r` to `h5ls` for more detail.

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

The figure tests live in `tests/test_plots.py` and use `pytest-mpl` for image comparison against baseline PNGs in `tests/baseline/`. Each test runs the full CLI pipeline (parsing → loading → adaptors → plotting) against small test datasets in `tests/data/` (test-2d: x=1,y=8,z=16; test-3d: x=4,y=4,z=4).

Other suites (plain `pytest`, no `--mpl` needed): `test_save.py`/`test_save_filename.py` (save formats and the `name_fragments`-derived filename), `test_idx_efficient.py` (asserts `Idx` prunes dask partitions instead of filtering), `test_particle_bp_vs_h5.py` + `test_h5_species_discovery.py` (loader parity/species discovery), `test_memory.py`, `test_particle_bp_perf.py`, `test_dask_graph.py`, and `test_synthetic_particles.py` (with the `synthetic_particles.py` generator).

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

1. `cli.main()` (`src/lib/cli.py`) builds `PscPlotConfig.from_env()`, configures dask, calls `parse_args()` (`src/lib/parsing/parse.py`) — a flat argparse parser with positional `prepath` + optional `variable` plus all registered adaptor/hook flags, returning an `Args` namespace (`src/lib/parsing/args.py`). It then calls `compile_action_nodes(args, config)` (`src/lib/data/compile.py`) and `.pull()`s each returned action node. (The `prepath` positional is **not** choices-constrained; an unknown prefix fails later in `get_loader`.)
2. Everything runs through a lazy, memoized **node graph** (`src/lib/data/node.py`). `compile_action_nodes` chains: `RootNode(config)` → `AdaptorNode(With(args.prepath, args.variable))` → one `AdaptorNode` per user adaptor → `PlotNode(hooks)` → action node(s): `ShowPlotNode` (`--show`, default on), `SavePlotNode` (`--save`), and/or `DaskGraphNode` (`--dask-graph`, renders the dask graph as SVG instead of plotting). Note the positional args are just an implicit **`--with`** — loading is `With`'s job, not a dedicated loader node. Each `DataProcessingNode` has a `@cache`d `pull()` and accumulates `name_fragments` (used to derive save filenames). If the adaptor list contains no `Versus`, a default `Versus(["y","z"], time_dim_rule="guess", color_dim=None)` is appended (`_with_versus`) — this is what selects axes/color/time dims and appends the plot target.
3. Data flows as a **`DataWorld`** (`src/lib/data/data_world.py`): a frozen dataclass holding `datas: dict[Prepath, DataWithAttrs]`, an `active_prepath: Prepath | None`, `plot_targets: list[PlotTarget]`, and `config`. `RootNode.pull()` returns an empty world; each `AdaptorNode` applies a `WorldAdaptor` to it. `active_data` returns `None` when there's no active prepath, `require_active_data()` raises; mutate with `with_active(data=…, prepath=…)` (sets/replaces the active entry) or `with_data(prepath, data)` (inserts without activating — what `Loader.apply_world` does). A `__post_init__` assert enforces that `active_prepath` is a key of `datas`. Holding **multiple named datas + multiple plot targets** is the "split vars" capability this branch is named for.
4. `PlotNode.pull()` calls `get_plot(world)` (`src/lib/plotting/get_plot.py`), which builds one `Renderer` **per `PlotTarget`**: `Field1dRenderer` when the target has no `color_dim`; `PolarFieldRenderer` / `Field2dRenderer` chosen by `SpatialDimsRTheta` / `SpatialDimsXY`; `ScatterRenderer` for `List` data with exactly 2 spatial dims. It wraps the renderer **list** in `StaticPlot` or `AnimatedPlot` based on `n_frames = max(r.get_n_frames())` — **animated iff `n_frames > 1`**, not on `time_dim` presence. Hooks are then attached via `plot.add_hook()`.
5. `ShowPlotNode`/`SavePlotNode.pull()` call `plot.show()` / `plot.save_to_path()`, which lazily `_initialize()` the figure (see the PlotInfo/AxesManager layer below).

### PlotTarget

`src/lib/data/plot_target.py`: a `PlotTarget[D, SD]` names one thing to draw — the `data` itself (a snapshot of the `DataWithAttrs` at the moment `Versus` ran, **not** a lookup key into `DataWorld.datas`), a `spatial_dims` (`SpatialDimsXY(x_dim, y_dim)` or `SpatialDimsRTheta(r_dim, theta_dim)`, both with `ndims` and `unpack()`), an optional `color_dim` and `time_dim`, and an `axes_loc: (col, row)` (1-based) selecting which subplot it lands in. `Versus.apply_world` is what constructs and appends targets (`-v … loc=i,j` sets `axes_loc`); multiple targets sharing an `axes_loc` are overlaid on one axes. Because the target captures the data, later adaptors in the pipeline don't retroactively affect already-appended targets — that's what makes `--copy x -i y=1 -v t --copy x -i y=-1 -v t` produce two independent curves.

### WorldAdaptor / Adaptor class hierarchy

`src/lib/data/adaptor.py`:
- `WorldAdaptor` (ABC) — single abstract `apply_world(world) -> DataWorld`. The shared node-graph interface for **both loaders and adaptors**. Adaptors that must touch the whole world (e.g. `Versus`, which reads `active_data` and appends a `PlotTarget`) override this directly.
- `Adaptor(WorldAdaptor)` — default `apply_world` = `world.with_active(data=self.apply(world.active_data))`. Override `apply_field`/`apply_list`; the unused one raises a friendly "use `--bin`/`--scatter`" error.
- `MetadataAdaptor(Adaptor)` — wraps `apply` to also modify the active variable's `VarInfo` in `var_infos` (used to derive axis labels/filenames). Override `get_modified_display_latex(metadata)` and/or `get_modified_unit_latex(metadata)`; both receive the current `metadata` so they can inspect e.g. `active_key` and `active_var_info`.
- `BareAdaptor(MetadataAdaptor)` — operates on the raw active variable (a single `xr.DataArray` for fields, a single `pd.Series`/`dd.Series` for lists) and doesn't touch metadata; override `apply_field_bare`/`apply_list_bare`.

### Auto-registration of loaders, adaptors, and hooks

`src/lib/__init__.py` imports `lib.data.loaders`, `lib.data.adaptors`, and `lib.plotting.hooks`, whose `__init__.py` files glob and `importlib.import_module` every sibling `*.py`.

**Loaders** (`src/lib/data/loaders/`) are `Loader` (a `WorldAdaptor` subclass) classes registered via the bare `@loader` decorator from `src/lib/data/loader.py`, which appends to `LOADERS: list[type[Loader]]`. Each loader exposes `discover_prefixes(cls, data_dir: Path) -> list[str]` and `suffix(cls)` classmethods, plus `get_data(config) -> DataWithAttrs`. Instances are constructed from a `Prepath` and store `self.prepath` / `self.subdir` / `self.prefix`; `get_data` must resolve files under `config.data_root / self.subdir`.

`discover_loaders(data_dir)` polls every registered loader's `discover_prefixes()` and returns a `dict[str, type[Loader]]`; `get_loader(data_root, prepath)` splits the prepath, discovers in `data_root / subdir`, and instantiates the loader matching the prefix. `load(config, prepath)` is the one-shot convenience used by `With` and `Derive`. On prefix conflicts, the later-registered loader wins with a `UserWarning`, so user-defined loaders can shadow built-ins. To add a new data source, drop a file into `src/lib/data/loaders/`, decorate the class with `@loader`, and implement `discover_prefixes`/`suffix`/`get_data`.

**Adaptors and hooks** register their argparse flags via the `@arg_parser(...)` / `@const_arg(...)` decorators in `src/lib/parsing/args_registry.py`, which append to the module-level `CUSTOM_ARGS` list. `parse._get_parser()` then iterates `CUSTOM_ARGS` and adds them to the parser. To add a new adaptor or hook, drop a new file into `src/lib/data/adaptors/` (or `src/lib/plotting/hooks/`) and decorate its parse function.

**Consequence:** a loader, adaptor, or hook that fails to register (e.g. import error in that file) will silently disappear from the CLI; suspect the auto-import if a flag or prefix goes missing.

### Data wrapper

`src/lib/data/data_with_attrs.py` defines `DataWithAttrs[Data, Subdata, MD]` and concrete `Field` (whole = `dict[str, xr.DataArray]`, sub = `xr.DataArray`), `FullList` (pandas) and `LazyList` (dask) (whole = `DataFrame`, sub = `Series`). The **whole/sub distinction is what the three type params encode** — `data` is the container, `__getitem__(key)` yields one subdata, `dims` lists the keys.

Frozen dataclasses; mutate via `assign(data=None, /, **metadata_vals)` (replaces data and/or metadata fields in one call), `with_info(key, info)`, or `with_active(*, data=, key=, info=)` — the latter is the workhorse: it writes the subdata into `data[key]`, updates `var_infos[key]`, and sets `active_key`, any subset of which may be omitted. Read the active variable via `active_key` / `active_subdata` / `active_info` (all `None`-tolerant) or `require_active_key()` / `require_active_subdata()` (raise a friendly error). Most code should use these rather than `data` directly; `BareAdaptor` handles it automatically via the shims in `adaptor.py`.

Two more abstract accessors both subclasses implement: `coordss(key=None) -> dict[DimKey, Coords]` (for `Field`, read off the xarray coords; for `List`, the explicit `ListMetadata.coordss`) and `bounds(key=None) -> Bounds` (defaults to the active key; **coordinates win over data values**, and the upper bound is extended by one cell width so it works as an image extent — falls back to a dask-computed min/max otherwise). `dask_collections()` returns the underlying dask objects, used by `--dask-graph`.

Type aliases live in `src/lib/data/types.py`: `DimKey` / `SubdataKey` / `VarKey` (all `str`, but they document intent), `SpeciesKey`, `Bounds`, `Coords`.

`Metadata` carries `prepath` (e.g. `"run5/pfd_moments"`), `active_key` (`SubdataKey | None`), `var_infos` (`dict[VarKey, VarInfo]` — maps all known variable/dimension keys), and `species`. `active_key` defaults to `None` — particle data may have no active variable (e.g. pure scatter of positions); `active_var_info` raises if so. `var_infos` is populated at load time from `src/lib/var_info_registry.py` via `lookup(prefix, key)` for every coordinate and the active variable. `FieldMetadata` adds nothing (it's a marker subclass). `ListMetadata` adds `coordss`, `weight_key`, and `subject: Latex | None` — what the list contains (e.g. "Particles", "Ions", "Electrons"); set by the particle loaders, refined by `SpeciesFilter`, used by `Bin` (distribution-function subscripts) and `ScatterRenderer` (titles). `ListMetadata` also carries optional `partition_dim: str | None` and `partition_ranges: list[tuple[int,int]] | None` — when set (currently by both particle loaders, with `partition_dim="t"`), they let `Idx.apply_list` prune by `df.partitions[...]` instead of a `df[df[dim] == pos]` predicate filter. **Loader invariant:** `partition_ranges` must describe the actual partition layout of the `dd.DataFrame` returned (one entry per value of `partition_dim`, each `(start, end)` matching the per-step `npartitions`). `LazyList.compute()` clears these fields because they describe the dask layout and become meaningless after materialization. The unusual `**` unpacking via `__getitem__` + `keys()` is what `Metadata.create_from` and `assign` use to round-trip values between subclasses (`FieldMetadata` vs `ListMetadata`).

> **Note (split-vars):** the `spatial_dims` / `time_dim` / `color_dim` axis-selection fields and the `name_fragments` that `Metadata` used to carry have moved out — geometry/axis selection now lives on `PlotTarget` (inside `DataWorld`), and `name_fragments` are accumulated by the node graph (`DataProcessingNode.name_fragments` / `HasNameFragments`).

### PlotInfo, renderers, Renderer2, and AxesManager

There are **two distinct "renderer" concepts**; keep them straight:

- **`Renderer[D, SD, PI]`** (`src/lib/plotting/renderer.py`) — *data → `PlotInfo`*. Constructed from a single `PlotTarget` (it reads `plot_target.data`; nothing is passed in separately), generic over the data type, spatial-dims type, and plot-info type. `__init__` calls `_init_plot_info()`; `_get_data_at_frame(frame)` applies `Idx({time_dim: frame})` to slice one frame; `get_n_frames()` is the length of the time coord (1 if no `time_dim`).
- **`Renderer2`** (`src/lib/plotting/renderer2.py`) — *`PlotInfo` → matplotlib*. A one-method ABC (`update()`) implemented by the artist setters in `src/lib/plotting/data_setter.py` (`LineSetter` / `ImageSetter` / `ScatterSetter` / `PolarMeshSetter`, each holding an artist + its info) and by `TreeLabeler`.

`PlotInfo` (`src/lib/plotting/plot_info.py`: `LineInfo` / `ImageInfo` / `ScatterInfo` / `PolarMeshInfo`, all `PlotInfo`/`PlotInfo2D`) describes *what* to draw: data arrays, per-dim `dim_scales` / `dim_bounds` / `dim_displays` / `dim_units`, `subject`, `scalar_coord_values` (for labels), `axes_index`, and `projection`. It is a **plain mutable dataclass** — the old `PlotInfo.set()` / `_setter_callbacks` push mechanism is gone. `update_plot_info(frame)` just assigns fields; propagation to matplotlib is a separate pull step.

`setup_fig(plot_infos)` (`src/lib/plotting/setup_fig.py`) is called once from `Plot._initialize()` and returns `(figure, list[Renderer2])`. It groups infos by `axes_index` into a subplot grid, then picks an `AxesManager` per axes: single info → `AxesManagerSingleLine` / `…Image` / `…Scatter` / `…PolarMesh`; several `LineInfo`s → `AxesManagerMultiLine` (shared axes + legend); one `ImageInfo` + `LineInfo`s → `AxesManagerImageAndLines` (lines on a twinned y-axis). Each manager's `setup()` creates the artists and appends the matching `Renderer2`s to `manager.renderers`, which `setup_fig` concatenates. Figures use `layout="constrained"`.

**Animation loop** (`AnimatedPlot._next_frame`): every `Renderer.update_plot_info(frame)` runs first, then every `Renderer2.update()`. So adding a new animatable property means (a) assigning it in `update_plot_info` and (b) reading it in the corresponding setter's `update()` — nothing else wires them together.

### Labels (TreeLabeler)

`src/lib/plotting/labeler.py` owns all text that describes *which data* is being shown (as opposed to axis labels). A label = an optional **subject** (variable name) + any number of **sublabels** (scalar coordinate values, e.g. `y = 1.000`). `TreeLabeler` is a tree of label sites — axes title at the root, per-line legend entries / colorbar label as leaves — each wrapping a `set_text` callable and optionally a source `PlotInfo`. `update()` walks to the root, which `_rebuild()`s bottom-up: components common to *all* children are **factored out** to the parent and removed from the children (so an overlay of `E_y` at three `y` values gets "E_y" in the title and just the `y` values in the legend). It's a `Renderer2`, so it re-runs each animation frame.

### Hooks

Hooks (`src/lib/plotting/hooks/`) — currently `--grid`, `--vline`, `--fit`, `--show-com` — subclass `Hook` (`src/lib/plotting/hook.py`) and implement `post_init_fig(message)` / `post_update_fig(message)`, receiving a `DrawMessage(plot_info, axes, frame_data)`. `PlotNode` attaches them and `Plot._initialize()` calls `post_init_fig` after building the figure. **Currently hooks are applied to the first renderer/axes only** — see the TODO in `plot.py`.

### Dimensions and var_infos

`src/lib/var_info.py` defines `VarInfo` as a frozen value (`display: Latex`, `unit: Latex`, `geometry`, `key`). `src/lib/var_info_registry.py` provides a single `_REGISTRY` dict keyed by `(prefix | None, key)` — `None`-prefix entries are shared dimensions (x, y, z, t); string-prefix entries are per-file-type variables (e.g. `("pfd", "hx_fc")` → `VarInfo(display="B_x", ...)`).
- `lookup(prefix, key)` — checks prefixed registry, then `None`-prefix registry, then Fourier toggle of the base key; falls back to a plain `VarInfo(display=key)`.

**Gotcha:** `lookup` keys on the bare **prefix**, never a `Prepath`. Passing a prepath is silent — it works at the data root (where prepath == prefix) and quietly falls through to the unprefixed/default `VarInfo` for a subdirectory prepath like `run5/pfd`, so every variable loses its display name and unit. Call sites holding a prepath must pass `split_prepath(prepath)[1]`.

**Per-instance invariant:** `metadata.var_infos` is the single source of truth for axis labels, coord-value labels, and Fourier/transform geometry checks during the pipeline. Adaptors that rename, add, or remove a dimension key (Fourier, TransformPolar, TransformSpherical, etc.) MUST update `var_infos` accordingly inside `apply_field` / `apply_list`. The `MetadataAdaptor` hooks (`get_modified_display_latex`/`get_modified_unit_latex`) only see post-apply metadata and only target the active variable's `VarInfo`, so dim-key swaps must be handled in `apply` itself, not via the hooks.

### Derived variables

`src/lib/derived_field_variables/registry.py` and `derived_particle_variables/registry.py` register computed variables per file prefix using `@derived_field_variable("pfd_moments")` decorators. The decorated function's parameter names declare the dependencies (raw or other derived variables); the loader resolves and computes them on demand.

`src/lib/data/ensure_derived.py` is the single entry point that resolves a key on demand: `ensure_derived(data, key)` dispatches on `Field` vs `List` to `derive_field_variable` / `derive_particle_variable`, using the prefix from `split_prepath(data.metadata.prepath)`. Both `With` and `Derive` call it, so any code path that names a variable gets registry-derived variables for free.

`--derive` works for both field and particle data. It can reference any variable already present or resolvable from the derived-variable registry, and updates `active_key` to point to the newly created variable.

`Derive` (`src/lib/data/adaptors/derive.py`) is a `WorldAdaptor` (overrides `apply_world`), not a plain `Adaptor`, because expressions may reference variables scoped to **another prepath** via the `::` operator (the same operator `--with` uses), e.g. `--derive electron_power="jy_ec*pfd_moments::jy_e"`. Unscoped names resolve against the active data; `prepath::key` names resolve against `world.datas[prepath]`, auto-loading it via `load(...)` (reusing it if already present) exactly as `--with` does. Both paths go through `ensure_derived`. Cross-prefix arrays are combined with xarray's default arithmetic alignment (no regridding). The Lark grammar has separate `variable : CNAME` and `scoped_variable : prepath "::" CNAME` rules; `prepath` currently matches `/[.\w\d]+/`, so **subdirectory prepaths don't work inside derive expressions yet** — `/` collides with division (see the TODO in the grammar).
