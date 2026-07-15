import sys
import warnings
import webbrowser
from pathlib import Path

import dask
import matplotlib.pyplot as plt

from lib import parsing
from lib.config import CONFIG
from lib.data.compile import _resolve_save_format, compile_args
from lib.parsing.args import Args


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
    save_dir.mkdir(exist_ok=True, parents=True)
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


def main():
    dask.config.set(num_workers=CONFIG.dask_num_workers)
    if CONFIG.dask_scheduler == "distributed":
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

    node = compile_args(args)
    plot = node.pull()

    if args.show:
        plot.show()
    if args.save is not None:
        args.save.mkdir(exist_ok=True, parents=True)

        if format not in plot.allowed_save_formats():
            if format == args.save_format:  # user actually specified this format
                message = f"{format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                warnings.warn(message)
            else:
                assert args.save_format is None

            format = plot.default_save_format()

        path = args.save / f"{node.get_save_file_stem()}.{format}"
        plot.save_to_path(path, dpi=args.save_dpi)
        print(f"wrote to {path}")
