import dask

from lib.config import PscPlotConfig
from lib.data.compile import compile_action_nodes
from lib.parsing.parse import parse_args


def main():
    config = PscPlotConfig.from_env()

    dask.config.set(num_workers=config.dask_num_workers)
    if config.dask_scheduler == "distributed":
        from dask.distributed import Client, LocalCluster

        cluster = LocalCluster(n_workers=config.dask_num_workers, threads_per_worker=1, processes=True)
        Client(cluster)
    elif config.dask_scheduler:
        dask.config.set(scheduler=config.dask_scheduler)

    args = parse_args()

    actions = compile_action_nodes(args, config)

    for action in actions:
        action.pull()
