import dask

from lib import parsing
from lib.config import CONFIG
from lib.data.compile import compile_action_nodes


def main():
    dask.config.set(num_workers=CONFIG.dask_num_workers)
    if CONFIG.dask_scheduler == "distributed":
        from dask.distributed import Client, LocalCluster

        cluster = LocalCluster(n_workers=CONFIG.dask_num_workers, threads_per_worker=1, processes=True)
        Client(cluster)
    elif CONFIG.dask_scheduler:
        dask.config.set(scheduler=CONFIG.dask_scheduler)

    args = parsing.get_parsed_args()

    actions = compile_action_nodes(args)

    for action in actions:
        action.pull()
