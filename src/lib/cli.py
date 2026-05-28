import sys
import warnings
import webbrowser
from pathlib import Path

import dask
import matplotlib.pyplot as plt

from lib import parsing
from lib.config import CONFIG
from lib.parsing.args import Args
from lib.plotting.plot import SaveFormat


def _resolve_save_format(args: Args) -> SaveFormat | None:
    if args.save is None:
        if args.save_format is not None:
            print("error: --save-format requires --save", file=sys.stderr)
            sys.exit(1)
        return None

    if args.save_format == "mp4":
        if not CONFIG.ffmpeg_bin:
            print("error: --save-format mp4 requires ffmpeg", file=sys.stderr)
            sys.exit(1)
        return "mp4"

    if args.save_format == "gif":
        return "gif"

    # save_format is None: try mp4, fall back to gif
    if CONFIG.ffmpeg_bin:
        return "mp4"

    message = "ffmpeg not found; will save animations as gif instead of mp4"
    warnings.warn(message)
    return "gif"


def _run_dask_graph(args: Args) -> None:
    data = args.get_data()

    collections = data.dask_collections()
    if not collections:
        print(
            f"error: --dask-graph requires dask-backed data; pipeline produced eager {type(data).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        import graphviz  # noqa: F401
    except ImportError:
        print(
            "error: --dask-graph requires the 'graphviz' package; install with `pip install -e \".[dask-graph]\"`",
            file=sys.stderr,
        )
        sys.exit(1)

    save_dir = args.save or Path.cwd()
    save_dir.mkdir(exist_ok=True)
    path = save_dir / f"{args.get_save_file_stem()}.daskgraph.svg"
    # dask.visualize's optimize_graph flag only lowers legacy HLG collections
    # (e.g. dask Arrays), not new-style Expr ones (dask DataFrames) — without
    # pre-optimizing the latter, un-lowered nodes (e.g. Concat from dd.concat)
    # fail with NotImplementedError in _layer.
    collections = [c.optimize() if hasattr(c, "optimize") else c for c in collections]
    dask.visualize(*collections, filename=str(path), optimize_graph=True)
    print(f"wrote to {path}")

    if args.show:
        webbrowser.open(path.absolute().as_uri())


def _init_mpi_scheduler() -> None:
    try:
        from dask_mpi import initialize
    except ImportError:
        print(
            "error: PSC_PLOT_DASK_SCHEDULER=mpi requires dask-mpi; install with 'pip install -e \".[mpi]\"'",
            file=sys.stderr,
        )
        sys.exit(1)
    from dask.distributed import Client

    initialize(nthreads=1)
    Client()


def main():
    dask.config.set(num_workers=CONFIG.dask_num_workers)
    if CONFIG.dask_scheduler == "mpi":
        _init_mpi_scheduler()
    elif CONFIG.dask_scheduler == "distributed":
        from dask.distributed import Client, LocalCluster

        cluster = LocalCluster(n_workers=CONFIG.dask_num_workers, threads_per_worker=1, processes=True)
        Client(cluster)
    elif CONFIG.dask_scheduler:
        dask.config.set(scheduler=CONFIG.dask_scheduler)

    args = parsing.get_parsed_args()

    if args.dask_graph:
        if args.save_format is not None:
            warnings.warn("--save-format is ignored with --dask-graph")
        _run_dask_graph(args)
        return

    # resolve format BEFORE applying pipeline in order to fail early
    format = _resolve_save_format(args)

    if format == "mp4":
        plt.rcParams["animation.ffmpeg_path"] = str(CONFIG.ffmpeg_bin)

    plot = args.get_animation()

    if args.show:
        plot.show()
    if args.save is not None:
        args.save.mkdir(exist_ok=True)

        if format not in plot.allowed_save_formats():
            if format == args.save_format:  # user actually specified this format
                message = f"{format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                warnings.warn(message)
            else:
                assert args.save_format is None

            format = plot.default_save_format()

        path = args.save / f"{args.get_save_file_stem()}.{format}"
        plot.save_to_path(path)
        print(f"wrote to {path}")
