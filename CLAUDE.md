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
- Adaptor flags such as `--roll`, `--reduce`, `--bin`, `--scatter`, `--mag`, `--nan0`, `--scale`, `--fourier`/`-f`, `--pos`, `--species`, `--transform-spherical`, `-v` (versus, sets axes), `-b` (bin)

Required environment (see `src/lib/config.py`):
- `PSC_PLOT_DATA_DIR` — directory containing the data files (must be set; `set_data_dir.sh <dir>` is a convenience script that exports it)
- `PSC_PLOT_FFMPEG_BIN` — optional, falls back to `which ffmpeg`; needed for saving animations
- `PSC_PLOT_DASK_NUM_WORKERS` — optional, defaults to 1
- `PSC_PLOT_DASK_CHUNK_SIZE` — optional, rows per dask partition for particle loads (default 1_000_000); reduce to bound peak memory on large files                         

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

## Architecture

The code lives under `src/lib/` and is organized around three concepts: **sources**, **adaptors**, and **plots**. Argument parsing wires them together.

### Data flow

1. `parsing.get_parsed_args()` (`src/lib/parsing/parse.py`) builds a flat argparse parser with positional `prefix` (choices-constrained to known prefixes) and optional `variable`, plus all registered adaptor/hook flags. Returns an `Args` namespace (`src/lib/parsing/args.py`) directly.
2. `args.get_animation()` checks whether `prefix` is a field or particle prefix and constructs the corresponding loader (`FieldLoader` or `ParticleLoader`), passing `variable` to set the optional initial active variable. It then calls `compile_source` (`src/lib/data/compile.py`) to wrap it in a `DataSourceWithPipeline` made of the user-supplied `Adaptor` list. If no `Versus` adaptor is present, a default one is appended (`y,z` vs `t`) — this is what selects axes and time dim.
3. `source.get_data()` loads raw data and runs the pipeline, returning a `DataWithAttrs` (a `Field` wrapping `xr.Dataset`, or a `List` wrapping `pd.DataFrame` / `dd.DataFrame`). `DataSource` is an ABC with a single abstract method `get_data()`.
4. `get_plot(data)` (`src/lib/plotting/get_plot.py`) picks a `Renderer` based on data type and geometry (`Field1dRenderer`, `Field2dRenderer`, `PolarFieldRenderer`, `ScatterRenderer`), then wraps it in `StaticPlot` or `AnimatedPlot` based on whether `time_dim` is present. `ScatterRenderer` requires exactly 2 `spatial_dims`. Each renderer defines `make_init_data`/`init` (one-time setup with frame 0) and `make_update_data`/`draw` (per-frame update for animations). Hooks are added to the plot object after construction.
5. Hooks (`src/lib/plotting/hooks/`) such as `--scale log`, `--grid`, `--vline`, `--fit` are appended onto the chosen plot before `show()`/`save()`.

### Auto-registration of adaptors and hooks

`src/lib/__init__.py` imports `lib.data.adaptors` and `lib.plotting.hooks`, whose `__init__.py` files glob and `importlib.import_module` every sibling `*.py`. Each module in those directories is responsible for registering itself with argparse via the `@arg_parser(...)` / `@const_arg(...)` decorators in `src/lib/parsing/args_registry.py`, which append to the module-level `CUSTOM_ARGS` list. `parse._get_parser()` then iterates `CUSTOM_ARGS` and adds them to the parser.

**Consequence:** to add a new adaptor or hook, drop a new file into `src/lib/data/adaptors/` (or `src/lib/plotting/hooks/`) and decorate its parse function — no central registry edit needed. Conversely, an adaptor that fails to register (e.g. import error in that file) will silently disappear from the CLI; suspect the auto-import if a flag goes missing.

### Adaptor class hierarchy

`src/lib/data/adaptor.py`:
- `Adaptor` — base. Override `apply_field`/`apply_list`; the unused one raises a friendly "use `--bin`/`--scatter`" error.
- `MetadataAdaptor` — wraps `apply` to also append name fragments and modify the active variable's `VarInfo` in `var_info` (used to derive saved filenames and axis labels). Override `get_modified_display_latex(metadata)` and/or `get_modified_unit_latex(metadata)`; both receive the current `metadata` so they can inspect e.g. `active_key` and `active_var_info`.
- `BareAdaptor` — for adaptors that operate on the active variable (a single `xr.DataArray` for fields, a single `pd.Series`/`dd.Series` for lists) and don't touch metadata.

`Pipeline` (`src/lib/data/pipeline.py`) is itself an `Adaptor` that chains a list of adaptors.

### Data wrapper

`src/lib/data/data_with_attrs.py` defines `DataWithAttrs[D, MD]` and concrete `Field` (`xr.Dataset`-backed), `FullList` (pandas), `LazyList` (dask). Frozen dataclasses; mutate via `assign_data` / `assign_metadata` / `assign`. `Metadata` carries `active_key` (`str | None`), `var_info` (`dict[str, VarInfo]` — maps all known variable/dimension keys to `VarInfo` objects), `name_fragments`, `spatial_dims`, `time_dim`, and `color_dim`. `active_key` defaults to `None` — particle data may have no active variable (e.g. pure scatter of positions). The convenience property `active_var_info` returns `var_info[active_key]`. `var_info` is populated at load time from `src/lib/field_units.py` via `lookup(prefix, key)` for every coordinate and the active variable. `FieldMetadata` also carries `prefix` (the file prefix, e.g. `"pfd_moments"`). The unusual `**` unpacking via `__getitem__` + `keys()` is what `Metadata.create_from` and `assign` use to round-trip values between subclasses (`FieldMetadata` vs `ListMetadata`).

Both `Field` and `List` expose an `active_data` property and `with_active_data()` method. For `Field`, `active_data` returns the `xr.DataArray` for `metadata.active_key`; `with_active_data(da)` replaces it and drops grid-incompatible siblings. For `List`, `active_data` returns the `pd.Series`/`dd.Series` column for `metadata.active_key`; `with_active_data(series)` replaces that column. Both raise `ValueError` if `active_key` is `None`. Most code should use `active_data` rather than `data` directly. `BareAdaptor` handles this automatically via the shims in `adaptor.py`.

The class-level `data: ...`/`metadata: ...` annotations on the subclasses look redundant but are intentional — see the comment in `DataWithAttrs.__init__`. They are needed so `isinstance`-narrowed code gets the concrete types; don't "clean them up."

### Dimensions and var_info

`src/lib/dimension.py` defines `VarInfo` as a frozen value (`name: Latex`, `unit: Latex`, `geometry`, `key`). `src/lib/field_units.py` provides the unified registries:
- `DIM_REGISTRY` — coordinate dimensions (x, y, z, t) with standard units.
- `PREFIXED_REGISTRY` — keyed by `(prefix, active_key)` for field and particle variables (e.g. `("pfd", "hx_fc")` → `VarInfo(name="B_x", ...)`).
- `lookup(prefix, key)` — checks prefixed registry, then dim registry, then Fourier toggle of the base key; falls back to a plain `VarInfo(name=key)`.

**Per-instance invariant:** `metadata.var_info` is the single source of truth for axis labels, coord-value labels, and Fourier/transform geometry checks during the pipeline. Adaptors that rename, add, or remove a dimension key (Fourier, TransformPolar, TransformSpherical, etc.) MUST update `var_info` accordingly inside `apply_field` / `apply_list`. The `MetadataAdaptor` hooks (`get_modified_display_latex`/`get_modified_unit_latex`) only see post-apply metadata and only target the active variable's `VarInfo`, so dim-key swaps must be handled in `apply` itself, not via the hooks.

### Derived variables

`src/lib/derived_field_variables/registry.py` and `derived_particle_variables/registry.py` register computed variables per file prefix using `@derived_field_variable("pfd_moments")` decorators. The decorated function's parameter names declare the dependencies (raw or other derived variables); the loader resolves and computes them on demand.

`--derive` works for both field and particle data. For fields, it operates on the underlying `xr.Dataset` and can reference any variable in the dataset or resolve names from the derived-variable registry (via `FieldMetadata.prefix`). It updates `metadata.active_key` to point to the newly created variable.
