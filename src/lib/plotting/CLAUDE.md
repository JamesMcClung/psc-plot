# CLAUDE.md — `src/lib/plotting`

Detail on the rendering layer: turning `PlotTarget`s into a matplotlib figure that can be re-driven each animation frame. The pipeline overview and `var_infos` live in the repo-root `CLAUDE.md`; `PlotTarget` itself is documented in `src/lib/data/CLAUDE.md`.

## PlotInfo, Renderer, and figure assembly (Grid / Panel / setters)

**`Renderer[D, SD, PI]`** (`src/lib/plotting/renderer.py`) — *data → `PlotInfo`*. Constructed from a single `PlotTarget` (it reads `plot_target.data`; nothing is passed in separately), generic over the data type, spatial-dims type, and plot-info type. `__init__` calls `_init_plot_info()`; `_get_data_at_frame(frame)` applies `Idx({time_dim: frame})` to slice one frame; `get_n_frames()` is the length of the time coord (1 if no `time_dim`). The concrete subclasses live in `src/lib/plotting/renderers/` (`field_1d` / `field_2d` / `polar_field` / `scatter`).

`PlotInfo` (`src/lib/plotting/plot_info.py`) describes *what* to draw: data arrays, per-dim `dim_scales` / `dim_bounds` / `dim_displays` / `dim_units`, `subject`, `scalar_coord_values` (for labels), `axes_index`, and `projection`. It is a **plain mutable dataclass** — `update_plot_info(frame)` just assigns fields; propagation to matplotlib is a separate pull step. Mixins declare which axes a shape has: `PlotInfo2D` (`x_dim`/`y_dim`), `PlotInfoColor` (`color_dim`), `PlotInfoMaybeColor` (optional `color_dim`); concrete shapes are `LineInfo` / `ImageInfo` / `ScatterInfo` / `PolarMeshInfo`. `has_legend()` / `has_colorbar()` are what drive the wiring below.

`setup_fig(plot_infos)` (`src/lib/plotting/setup_fig.py`) is called once from `Plot._initialize()` and returns `(Figure, Grid)`. Figures use `layout="constrained"`.

- **`Grid`** (`grid.py`) groups infos by `axes_index`, creates one subplot per location (rejecting mixed `projection`s), and owns a `Panel` per location plus the figure suptitle labeler. `Grid.update()` = `update_data()` → `update_bounds()` → `update_labels()`.
- **`Panel`** (`panel.py`) holds everything attached to one axes location: data setters, and per-axis dicts of bounds setters, unit labelers, and scales (keyed by `(Axes, AxId)`, so a twinned right-hand axis is just another key). It is built through `wire_*` methods, each paired with a `can_wire_*` predicate that tests compatibility *before* committing.
- **`setup_panel_xy`** (`setup_fig.py`) is the placement algorithm. It sorts infos so legend-capable ones come last, then for each info wires the x-axis (incompatible → hard error) and tries the left y-axis; if that fails and the info has a legend, it twins a right y-axis and tries again. There is no per-shape dispatch and no image-vs-line special case — placement is decided purely by unit/scale compatibility.
- **`DataSetter`** (`data_setter.py`) holds an artist + its info; `DataSetter.dispatch_init(ax, info)` picks `LineSetter` / `ImageSetter` / `ScatterSetter` / `PolarMeshSetter`, and `update()` pushes info → artist.
- **`BoundsSetter`** (`bounds_setter.py`) holds every info sharing one axis and sets the widest of their bounds, skipping the matplotlib call when unchanged.
- **`AxId`** (`axis_id.py`) is the `"x" | "y" | "r"` literal that keys all the per-axis dicts.

**Animation loop** (`AnimatedPlot._next_frame`): every `Renderer.update_plot_info(frame)` runs first, then `Grid.update()`. So adding a new animatable property means (a) assigning it in `update_plot_info` and (b) reading it in the corresponding setter's `update()` — nothing else wires them together.

## Labels (Labeler)

`src/lib/plotting/labeler.py` owns all figure text. `Labeler` is just a wrapper around a `set_text` callable; three kinds build on it:

- **`SubjectLabeler`** — text describing *which data* is shown: an optional **subject** (variable name) + any number of **sublabels** (scalar coordinate values, e.g. `y = 1.000`). These form a tree of label sites — figure suptitle above axes titles above per-line legend entries / colorbar labels — each optionally carrying a source `PlotInfo`. `update()` walks to the root, which `_rebuild()`s bottom-up: components common to *all* children are **factored out** to the parent and removed from the children (so an overlay of `E_y` at three `y` values gets "E_y" in the title and just the `y` values in the legend). `Grid` wires the suptitle only once a second panel appears.
- **`UnitLabeler`** — axis and colorbar text (`display [unit]`). It holds several sources and raises if they disagree on unit (or on display, unless `require_display_match=False`, as for the y-axis). `is_compatible(info)` is a trial append/rollback — that's what `Panel.can_wire_unit_labeler_xy` uses to decide left-vs-right y-axis.
- **`SubjectAndUnitLabeler`** — composes both for a colorbar whose color dim *is* the subject, delegating to an inner `SubjectLabeler` (which joins the title tree) and `UnitLabeler`.

Labelers are driven by `Grid.update_labels()` each animation frame. `Panel.update_labels()` also adds/removes the axes legend depending on whether any label text survived factoring.

## Hooks

Hooks (`src/lib/plotting/hooks/`) — currently `--grid`, `--vline`, `--fit`, `--show-com` — subclass `Hook` (`src/lib/plotting/hook.py`) and implement `post_init_fig(message)` / `post_update_fig(message)`, receiving a `DrawMessage(plot_info, axes, frame_data)`. `PlotNode` attaches them and `Plot._initialize()` calls `post_init_fig` after building the figure. **Currently hooks are applied to the first renderer/axes only** — see the TODO in `plot.py`.
