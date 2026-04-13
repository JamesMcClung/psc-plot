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
psc-plot <prefix> <variable> [options]
```

Or directly via `py src/main.py <prefix> <variable> [options]` (backward-compatible).

Where `<prefix>` selects the data source: field prefixes (`pfd`, `pfd_moments`, `gauss`, `continuity`) or particle prefixes (`prt`). Examples live in `plots/check.sh` and `plots/check2.sh` and serve as the de-facto smoke tests / usage reference.

Common flags:
- `-q` quiet (don't show interactively), `-s [dir]` save output (defaults to `.` if dir omitted)
- Adaptor flags such as `--roll`, `--reduce`, `--bin`, `--scatter`, `--mag`, `--nan0`, `--scale`, `--fourier`/`-f`, `--pos`, `--species`, `--transform-spherical`, `-v` (versus, sets axes), `-b` (bin)

Required environment (see `src/lib/config.py`):
- `PSC_PLOT_DATA_DIR` — directory containing the data files (must be set; `set_data_dir.sh <dir>` is a convenience script that exports it)
- `PSC_PLOT_FFMPEG_BIN` — optional, falls back to `which ffmpeg`; needed for saving animations
- `PSC_PLOT_DASK_NUM_WORKERS` — optional, defaults to 1

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

Running `plots/check*.sh` against a real data directory remains useful for manual validation of more complex scenarios.

## Architecture

The code lives under `src/lib/` and is organized around three concepts: **sources**, **adaptors**, and **plots**. Argument parsing wires them together.

### Data flow

1. `parsing.get_parsed_args()` (`src/lib/parsing/parse.py`) builds an argparse parser with one subparser per file prefix, each populated with the same shared set of optional arguments. The parsed namespace is converted to a typed `FieldArgs` or particle-equivalent (`args_base.ArgsUntyped.to_typed`).
2. The typed args' `get_animation()` constructs a `FieldLoader`/particle loader (a `DataSource`), then calls `compile_source` (`src/lib/data/compile.py`) to wrap it in a `DataSourceWithPipeline` made of the user-supplied `Adaptor` list. If no `Versus` adaptor is present, a default one is appended (`y,z` vs `t`) — this is what selects axes and time dim.
3. `source.get_data()` loads raw data and runs the pipeline, returning a `DataWithAttrs` (a `Field` wrapping `xr.Dataset`, or a `List` wrapping `pd.DataFrame` / `dd.DataFrame`).
4. `get_plot(data)` (`src/lib/plotting/get_plot.py`) dispatches on `data` type and `metadata.spatial_dims`/`time_dim` to choose a concrete `Plot` subclass (static/animated, 1D/2D, polar, scatter).
5. Hooks (`src/lib/plotting/hooks/`) such as `--scale log`, `--grid`, `--vline`, `--fit` are appended onto the chosen plot before `show()`/`save()`.

### Auto-registration of adaptors and hooks

`src/lib/__init__.py` imports `lib.data.adaptors` and `lib.plotting.hooks`, whose `__init__.py` files glob and `importlib.import_module` every sibling `*.py`. Each module in those directories is responsible for registering itself with argparse via the `@arg_parser(...)` / `@const_arg(...)` decorators in `src/lib/parsing/args_registry.py`, which append to the module-level `CUSTOM_ARGS` list. `field_args.add_field_subparsers` then iterates `CUSTOM_ARGS` and adds them to every prefix's parser.

**Consequence:** to add a new adaptor or hook, drop a new file into `src/lib/data/adaptors/` (or `src/lib/plotting/hooks/`) and decorate its parse function — no central registry edit needed. Conversely, an adaptor that fails to register (e.g. import error in that file) will silently disappear from the CLI; suspect the auto-import if a flag goes missing.

### Adaptor class hierarchy

`src/lib/data/adaptor.py`:
- `Adaptor` — base. Override `apply_field`/`apply_list`; the unused one raises a friendly "use `--bin`/`--scatter`" error.
- `MetadataAdaptor` — wraps `apply` to also append name fragments and modify `var_latex` (used to derive saved filenames and axis labels).
- `BareAdaptor` — for adaptors that operate on the raw `xr.DataArray` / DataFrame and don't touch metadata.

`Pipeline` (`src/lib/data/pipeline.py`) is itself an `Adaptor` that chains a list of adaptors.

### Data wrapper

`src/lib/data/data_with_attrs.py` defines `DataWithAttrs[D, MD]` and concrete `Field` (`xr.Dataset`-backed), `FullList` (pandas), `LazyList` (dask). Frozen dataclasses; mutate via `assign_data` / `assign_metadata` / `assign`. `Metadata` carries `var_name`, `var_latex`, `name_fragments`, `spatial_dims`, `time_dim`, `color_dim`. `FieldMetadata` also carries `prefix` (the file prefix, e.g. `"pfd_moments"`). The unusual `**` unpacking via `__getitem__` + `keys()` is what `Metadata.create_from` and `assign` use to round-trip values between subclasses (`FieldMetadata` vs `ListMetadata`).

`Field.data` is an `xr.Dataset` containing multiple variables; `Field.active_data` returns the `xr.DataArray` for `metadata.var_name` (the variable being plotted). `Field.with_active_data(da)` replaces the active variable and drops sibling variables that are no longer grid-compatible. Most code should use `active_data` rather than `data` directly. `BareAdaptor.apply_field` handles this automatically via the shim in `adaptor.py`.

The class-level `data: ...`/`metadata: ...` annotations on the subclasses look redundant but are intentional — see the comment in `DataWithAttrs.__init__`. They are needed so `isinstance`-narrowed code gets the concrete types; don't "clean them up."

### Derived variables

`src/lib/derived_field_variables/registry.py` and `derived_particle_variables/registry.py` register computed variables per file prefix using `@derived_field_variable("pfd_moments")` decorators. The decorated function's parameter names declare the dependencies (raw or other derived variables); the loader resolves and computes them on demand.

`--derive` works for both field and particle data. For fields, it operates on the underlying `xr.Dataset` and can reference any variable in the dataset or resolve names from the derived-variable registry (via `FieldMetadata.prefix`). It updates `metadata.var_name` to point to the newly created variable.
