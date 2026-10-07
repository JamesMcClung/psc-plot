import dask

from lib.config import PscPlotConfig
from lib.run.usage_error import UsageError


def configure_dask(config: PscPlotConfig):
    dask.config.set(num_workers=config.dask_num_workers)
    if config.dask_scheduler == "distributed":
        try:
            from dask.distributed import Client, LocalCluster
        except ImportError:
            raise UsageError("PSC_PLOT_DASK_SCHEDULER is 'distributed', which requires the 'distributed' package; install with `pip install -e \".[hpc]\"`") from None

        cluster = LocalCluster(n_workers=config.dask_num_workers, threads_per_worker=1, processes=True)
        Client(cluster)
    else:
        dask.config.set(scheduler=config.dask_scheduler)
