# CLAUDE.md — `src/lib/plotting`

Detail on the rendering layer: turning `PlotTarget`s into a matplotlib figure that can be re-driven each animation frame. The pipeline overview and `var_infos` live in the repo-root `CLAUDE.md`; `PlotTarget` itself is documented in `src/lib/data/CLAUDE.md`.

## PlotInfo, Renderer, and figure assembly (Grid / Panel / setters)

**`Renderer[D, SD, PI]`** (`src/lib/plotting/renderer.py`) — *data → `PlotInfo`*. Constructed from a single `PlotTarget` (it reads `plot_target.data`; nothing is passed in separately), generic over the data type, spatial-dims type, and plot-info type. `__init__` calls `_init_plot_info()`; `_get_data_at_frame(frame)` applies `Idx({time_dim: frame})` to slice one frame; `get_n_frames()` is the length of the time coord (1 if no `time_dim`). The concrete subclasses live in `src/lib/plotting/renderers/` (`field_1d` / `field_2d` / `polar_field` / `scatter`).

`PlotInfo` (`src/lib/plotting/plot_info.py`) describes *what* to draw: data arrays, per-dim `dim_scales` / `dim_bounds` / `dim_displays` / `dim_units`, `subject_dim` (the dim that *is* the plotted variable: `y_dim` for a 1D field, `color_dim` for 2D/polar, `None` for scatter), `scalar_coord_values` (for labels), `axes_index`, and `projection`. It is a **plain mutable dataclass** — `update_plot_info(frame)` just assigns fields; propagation to matplotlib is a separate pull step. Mixins declare which axes a shape has: `PlotInfo2D` (`x_dim`/`y_dim`), `PlotInfoColor` (`color_dim`), `PlotInfoMaybeColor` (optional `color_dim`); concrete shapes are `LineInfo` / `ImageInfo` / `ScatterInfo` / `PolarMeshInfo`. `has_legend()` / `has_colorbar()` are what drive the wiring below.

`setup_fig(plot_infos)` (`src/lib/plotting/setup_fig.py`) is called once from `Plot._initialize()` and returns `(Figure, Grid)`. Figures use `layout="constrained"`.

- **`Grid`** (`grid.py`) groups infos by `axes_index`, creates one subplot per location (rejecting mixed `projection`s), and owns a `Panel` per location plus the figure suptitle labeler. `Grid.update()` = `update_data()` → `update_bounds()` → `update_interior_x_ticks()` → `update_labels()` → `adjust_to_last_draw()` (the last two are explained under *Stacked panels* below).
- **`Panel`** (`panel.py`) holds everything attached to one axes location: data setters, per-axis dicts of bounds setters and scales (keyed by `(Axes, AxId)`, so a twinned right-hand axis is just another key), and x/y axis labelers keyed by `Axes`. It is built through `wire_*` methods, each paired with a `can_wire_*` predicate that tests compatibility *before* committing.
- **`setup_panel_xy`** (`setup_fig.py`) is the placement algorithm. It sorts infos so legend-capable ones come last, then for each info wires the x-axis (incompatible → hard error) and tries the left y-axis; if that fails and the info has a legend, it twins a right y-axis and tries again. There is no per-shape dispatch and no image-vs-line special case — placement is decided purely by unit/scale compatibility.
- **`DataSetter`** (`data_setter.py`) holds an artist + its info; `DataSetter.dispatch_init(ax, info)` picks `LineSetter` / `ImageSetter` / `ScatterSetter` / `PolarMeshSetter`, and `update()` pushes info → artist.
- **`BoundsSetter`** (`bounds_setter.py`) holds every info sharing one axis and sets the widest of their bounds, skipping the matplotlib call when unchanged.
- **`AxId`** (`axis_id.py`) is the `"x" | "y" | "r"` literal that keys all the per-axis dicts.

**Animation loop** (`AnimatedPlot._next_frame`): every `Renderer.update_plot_info(frame)` runs first, then `Grid.update()`. So adding a new animatable property means (a) assigning it in `update_plot_info` and (b) reading it in the corresponding setter's `update()` — nothing else wires them together.

## Stacked panels (shared x axes)

`Grid.share_x_axes_vertically()` makes each vertically adjacent pair of panels share its x axis where it can (`Panel.try_share_x_axis`, which also drops the upper panel's bottom x labels and ticks, and both titles), splitting each column into **stacks**. If any stack has more than one panel, `_remove_vertical_space()` pushes each stack's panels flush together:

- **Zero `h_pad`/`hspace`**, then put the figure's own top/bottom padding back via the layout `rect` and a suptitle transform offset, since `h_pad` controls both. Both are figure-wide, so between stacks `Panel.pad_y_end` puts `h_pad` back on each side: an invisible in-layout `AnnotationBbox` spacer anchored beyond the x label / title (padding the text itself would only move it away from its own axes).
- **y tick labels**: every end a panel has in a stack goes into its `flush_y_ends` (including the stack's bottom, so all panels follow the same rules). `tuck_y_tick_labels` then anchors any label overhanging a flush end so it sits inside the axes (`va="bottom"` at the lower end, `"top"` at the upper). Panels below another also `prune_y_ticks("upper")`, so their top label doesn't crowd the bottom label of the panel above. Flush-marking and pruning are deliberately separate.
- **Interior x ticks**: `Panel.add_interior_x_ticks` draws ticks just inside the top and bottom of every panel in a stack; the bottom panel keeps its outward axis ticks too. They're **separate scatter artists**, not the axis' own ticks, because matplotlib points all ticks on an edge one way and gives them one color. Each is colored against the data beneath it via `DataSetter.get_colors_within` (only images implement it so far).
- **Colorbars**: all colorbars (stacked or not) use `shrink=0.8`, set in `setup_colorbar`. Down a column, `right_align_cbar_labels` lines up the colorbar labels' right edges. A linear colorbar's power-of-ten multiplier becomes the first line of its label (`×10^{n}`, nearest the tick labels), put there by `Panel.wire_cbar_label`.

**Per-frame steps and when they may run.** `Grid.adjust_to_last_draw()` (`tuck_y_tick_labels`, `right_align_cbar_labels`) **measures where things were last drawn**, so it must run after a layout. `setup_fig` does a `draw_without_rendering()` for it, and it reruns every frame in `Grid.update()`, each frame using the previous draw. `update_interior_x_ticks` measures nothing: it places and samples through the axes' transforms, so it can run anywhere after `update_bounds()`.

Rules learned the hard way:
- **Pin anything positioned from a measurement in fixed units** (points or inches, e.g. `transAxes + ScaledTranslation`), never as a fraction of an axes' size. The next layout can resize the axes; for example, tucking labels makes axes taller, which widens their colorbars. A fraction then goes stale, which once gave movies a first frame laid out differently from the rest.
- **Anything that mustn't affect spacing must be out of layout** (`set_in_layout(False)`). Constrained layout reserves room for every in-layout artist's extent. Note that a spine's extent includes any ticks pointing outward past it, so the direction of the axis' own ticks changes the layout.
- **Check movies, not just stills**: bugs from measuring the last draw only show when frames are compared. Render the same layout as both a PNG (`-i t=…`) and an MP4, and compare extracted frames (`ffmpeg -vf "select='eq(n\,0)+eq(n\,1)'" -vsync 0 f%d.png`), e.g. by checking that the axes spines land on the same pixel columns.

## Labels (Labeler)

`src/lib/plotting/labeler.py` owns all figure text. `Labeler` is just a wrapper around a `set_text` callable.

- **`SubjectLabeler`** — text describing *which data* is shown: an optional **subject** + any number of **sublabels** (scalar coordinate values, e.g. `y = 1.000`). These form a tree of label sites — figure suptitle above axes titles above y axes / colorbars above legend entries. A node with a `source` `PlotInfo` is a leaf and reads its labels from it; any other node factors out what **all** its children have in common. `update()` walks to the root, which `_rebuild()`s bottom-up.
  - A parent sees a child only through `_get_liftable_subject` / `_get_liftable_sublabels` and factors it out with `_lift_subject` / `_lift_sublabels`; subclasses override these, and the parent never special-cases a subclass. Children whose `_labels_any_data()` is false (e.g. a y axis holding only an image) are ignored, so they don't block their siblings. A `None` subject is never lifted, since a forwarding node would pass the lift to children with differing subjects.
  - `subject` is `PlotInfo.subject`: the display of `subject_dim`, **without its unit**; for scatter, `ScatterInfo.list_subject`.
- **`YAxisLabeler`** — a y axis's `display [unit]`, via a wrapped `UnitLabeler(require_display_match=False)`. Its children are the legend entries of lines whose `subject_dim` is their `y_dim` (other legend entries hang off the title). When the axis shows a display, that *is* their subject, so it **absorbs** it from them and the subject appears only on the axis. Otherwise it's transparent: it offers, and forwards lifts of, whatever its children have in common.
- **`ColorbarLabeler`** — a leaf for a colorbar whose `color_dim` is the `subject_dim`: `subject (sublabels) [unit]`. It never offers its subject, so the title gets only the sublabels.
- **`UnitLabeler`** — plain axis/colorbar text (`display [unit]`): x axes, and colorbars not of the subject (e.g. scatter color). It holds several sources and raises if they disagree on unit (or on display, if `require_display_match`). `is_compatible(info)` is a trial append/rollback — that's what `Panel.can_wire_unit_labeler_xy` uses to decide left-vs-right y-axis.

`Grid` wires the suptitle only once a second panel appears; stacking panels removes their titles, reparenting their children to the suptitle.

Labelers are driven by `Grid.update_labels()` each animation frame. `Panel.update_labels()` also adds/removes the axes legend depending on whether any label text survived factoring.

## Hooks

Hooks (`src/lib/plotting/hooks/`) — currently `--grid`, `--vline`, `--fit`, `--show-com` — subclass `Hook` (`src/lib/plotting/hook.py`) and implement `post_init_fig(message)` / `post_update_fig(message)`, receiving a `DrawMessage(plot_info, axes, frame_data)`. `PlotNode` attaches them and `Plot._initialize()` calls `post_init_fig` after building the figure. **Currently hooks are applied to the first renderer/axes only** — see the TODO in `plot.py`.
