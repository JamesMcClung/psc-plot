from lib.data.adaptor import Adaptor
from lib.data.adaptors.field_adaptors.versus import Versus
from lib.data.pipeline import Pipeline
from lib.data.source import DataSource, DataSourceWithPipeline


def compile_source(loader: DataSource, adaptors: list[Adaptor]) -> DataSource:
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], "t", color_dim=None))

    pipeline = Pipeline(*adaptors)
    source = DataSourceWithPipeline(loader, pipeline)

    return source
