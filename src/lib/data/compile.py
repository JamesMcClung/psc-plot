from lib.data.adaptor import Adaptor
from lib.data.adaptors.versus import Versus
from lib.data.data_source import DataSource, DataSourceWithPipeline
from lib.data.pipeline import Pipeline


def compile_source(loader: DataSource, adaptors: list[Adaptor]) -> DataSource:
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], "t", color_dim=None))

    pipeline = Pipeline(*adaptors)
    source = DataSourceWithPipeline(loader, pipeline)

    return source
