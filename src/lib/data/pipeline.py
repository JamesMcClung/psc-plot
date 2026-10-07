from dataclasses import dataclass

from lib.data.adaptor import WorldAdaptor
from lib.data.data_world import DataWorld
from lib.profiling.profiler import profile_stage


def _stage_name(adaptor: WorldAdaptor) -> str:
    """The adaptor's class name, plus its name fragments; the CLI text isn't kept after parsing."""
    name = type(adaptor).__name__
    if fragments := adaptor.get_name_fragments():
        name += f" ({'-'.join(fragments)})"
    return name


@dataclass(frozen=True)
class Pipeline:
    """A sequence of adaptors applied to a world in turn: the user's CLI pipeline, or a derived variable's."""

    adaptors: tuple[WorldAdaptor, ...]

    def get_name_fragments(self) -> list[str]:
        return [frag for adaptor in self.adaptors for frag in adaptor.get_name_fragments()]

    def run(self, world: DataWorld) -> DataWorld:
        for adaptor in self.adaptors:
            with profile_stage(_stage_name(adaptor)):
                world = adaptor.apply_world(world)
        return world
