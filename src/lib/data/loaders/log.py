import pathlib
import re

import pandas as pd

from lib.config import PscPlotConfig
from lib.data.data_with_attrs import FullList, ListMetadata
from lib.data.loader import Loader, loader
from lib.latex import Latex

_FLOAT = r"[-+\d.eE]+"
_STEP_LINE_RE = re.compile(rf"^\*+ Step (\d+) / \d+, Code Time ({_FLOAT}), Wall Time ({_FLOAT})")


def parse_log(path: pathlib.Path) -> pd.DataFrame:
    """Parse the `**** Step <n> / <nt>, Code Time <t>, Wall Time <s>` lines of a PSC log."""
    rows = []
    with open(path) as file:
        for line in file:
            if m := _STEP_LINE_RE.match(line):
                rows.append((int(m.group(1)), float(m.group(2)), float(m.group(3))))
    return pd.DataFrame(rows, columns=["step", "code_time", "wall_time"])


@loader
class LogLoader(Loader):
    """A PSC stdout log (any `log*.txt`, e.g. `log.txt` or `log2.txt`), as one row per step."""

    @classmethod
    def discover_prefixes(cls, data_dir: pathlib.Path) -> list[str]:
        return sorted(path.name.removesuffix(f".{cls.suffix()}") for path in data_dir.glob(f"log*.{cls.suffix()}") if path.is_file())

    @classmethod
    def suffix(cls):
        return "txt"

    def get_data(self, config: PscPlotConfig) -> FullList:
        df = parse_log(config.data_root / self.subdir / f"{self.prefix}.{self.suffix()}")
        metadata = ListMetadata(
            prepath=self.prepath,
            var_infos={key: config.registry.lookup(self.prefix, key) for key in df.columns},
            subject=Latex(r"\text{Steps}"),
        )
        return FullList(df, metadata)
