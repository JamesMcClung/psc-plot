import dask
import matplotlib

from lib.config import PscPlotConfig
from lib.data.compile import compile_action_nodes
from lib.parsing.parse import parse_args
from lib.profiling.environment import EnvironmentReport
from lib.profiling.profiler import Profiler
from lib.profiling.report import ProfileReport
from lib.profiling.sampler import ProcessTreeSampler


def main():
    config = PscPlotConfig.from_env()

    dask.config.set(num_workers=config.dask_num_workers)
    if config.dask_scheduler == "distributed":
        from dask.distributed import Client, LocalCluster

        cluster = LocalCluster(n_workers=config.dask_num_workers, threads_per_worker=1, processes=True)
        Client(cluster)
    else:
        dask.config.set(scheduler=config.dask_scheduler)

    args = parse_args()

    if args.profile:
        # never show a window; see compile_action_nodes
        matplotlib.use("Agg")

    actions = compile_action_nodes(args, config)

    if not args.profile:
        for action in actions:
            action.pull()
        return

    # collected after dask setup, so a distributed cluster's workers already exist
    environment = EnvironmentReport.collect(config)
    if not args.adaptors:
        print(environment.format_text())
        return

    with ProcessTreeSampler() as sampler:
        profiler = Profiler(sampler)
        with profiler.run():
            for action in actions:
                action.pull()

    print()
    print(ProfileReport(environment, profiler.records, profiler.total).format_text())
