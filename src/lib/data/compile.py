from lib.data.adaptor import Adaptor
from lib.data.adaptors.field_adaptors.versus import Versus
from lib.data.pipeline import Pipeline
from lib.data.source import DataSource, DataSourceWithPipeline


def compile_source(loader: DataSource, adaptors: list[Adaptor]) -> DataSource:
    spatial_dims = ["y", "z"]
    time_dim: str = "t"

    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            spatial_dims = adaptor.spatial_dims
            time_dim = adaptor.time_dim
            break
    else:
        adaptors.append(Versus(spatial_dims, time_dim, color_dim=None))

    pipeline = Pipeline(*adaptors)
    source = DataSourceWithPipeline(loader, pipeline)

    return source
