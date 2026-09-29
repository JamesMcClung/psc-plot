from contextvars import ContextVar

from lib.config import PscPlotConfig
from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.data.data_world import DataWorld
from lib.data.types import SubdataKey
from lib.file_util import Prepath, split_prepath

# The (prepath, key) pairs currently being derived, outermost first, for cycle detection.
_DERIVING: ContextVar[tuple[tuple[Prepath, SubdataKey], ...]] = ContextVar("_DERIVING", default=())


def ensure_derived[D: DataWithAttrs](data: D, key: SubdataKey, config: PscPlotConfig) -> D:
    """Return `data` with `key` present, deriving it from the registry if needed.

    A derived variable's pipeline runs in an isolated world seeded with `data`; only its final active variable is kept, stored under `key`. Temporaries, and any other prepaths the pipeline loads, are discarded. `data`'s active key is unchanged.
    """
    if key in data:
        return data

    prepath = data.metadata.prepath
    _, prefix = split_prepath(prepath)
    pipeline = config.registry.pipeline(prefix, key)
    if pipeline is None:
        message = f"""No variable named '{key}'.
The following variables are defined:    {list(data.data)}.
The following variables can be derived: {config.registry.derivable_keys(prefix)}."""
        raise ValueError(message)

    chain = _DERIVING.get()
    if (prepath, key) in chain:
        cycle = [chain_key for _, chain_key in chain[chain.index((prepath, key)) :]] + [key]
        raise ValueError(f"Cyclic derived variable: {' -> '.join(cycle)}")

    token = _DERIVING.set((*chain, (prepath, key)))
    try:
        world = DataWorld({prepath: data}, prepath, config=config)
        for step in pipeline:
            world = step.apply_world(world)
    finally:
        _DERIVING.reset(token)

    final = world.require_active_data()
    result = final.require_active_subdata()

    new_var_infos = data.metadata.var_infos.copy()
    if isinstance(data, Field):
        # e.g. k_x after --fourier: take the pipeline's var info for dims the source didn't have
        for dim in result.coords:
            if dim not in new_var_infos and dim in final.metadata.var_infos:
                new_var_infos[dim] = final.metadata.var_infos[dim]
        new_data = data.data | {key: result}
    elif isinstance(data, List):
        new_data = data.data.assign(**{key: result})
    else:
        raise TypeError(data.__class__)
    new_var_infos[key] = config.registry.lookup(prefix, key)

    return data.assign(new_data, var_infos=new_var_infos)


def get_derivable_keys(data: DataWithAttrs, config: PscPlotConfig) -> list[SubdataKey]:
    _, prefix = split_prepath(data.metadata.prepath)
    return config.registry.derivable_keys(prefix)
