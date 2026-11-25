from typing import Any

from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import DataWithAttrs, Field
from lib.data.data_world import DataWorld
from lib.data.ensure_derived import ensure_derived
from lib.data.expression import EXPRESSION_PARSER, ExpressionEvaluator, evaluate
from lib.data.loader import get_or_load
from lib.file_util import split_prepath
from lib.parsing.args_registry import arg_parser


class Derive(WorldAdaptor):
    def __init__(self, expression: str):
        self.expression = expression
        self.ast = EXPRESSION_PARSER.parse(expression)

    def apply_world(self, world):
        return evaluate(AssignNewVariable(world), self.ast)

    def get_name_fragments(self):
        return [f'derive_"{self.expression}"']


class AssignNewVariable(ExpressionEvaluator):
    def __init__(self, world: DataWorld):
        self.world = world
        super().__init__()

    def variable(self, toks: list):
        key = str(toks[0])
        _, value = self._resolve(self.world.require_active_data(), key)
        return value

    def scoped_variable(self, toks: list):
        [prepath, key] = [str(tok) for tok in toks]
        data, value = self._resolve(get_or_load(self.world, prepath), key)
        self.world = self.world.with_data(prepath, data)
        return value

    def _resolve(self, data: DataWithAttrs, key: str) -> tuple[DataWithAttrs, Any]:
        """`key`'s values: a variable, else a field's coord, else a derived variable (which the returned data then holds)."""
        if key not in data and isinstance(data, Field) and (coord := data.coord(key)) is not None:
            return data, coord
        data = ensure_derived(data, key, self.world.config)
        return data, data[key]

    def assignment(self, toks: list):
        [key, subdata] = toks
        data = self.world.require_active_data()
        _, prefix = split_prepath(data.metadata.prepath)
        info = self.world.config.registry.lookup(prefix, key)
        data = data.with_active(data=subdata, key=key, info=info)
        return self.world.with_active(data=data)


_DERIVE_FORMAT = "new_var_key=expression"


@arg_parser(
    dest="adaptors",
    flags="--derive",
    metavar=_DERIVE_FORMAT,
    help=f"Create a new variable with the given name. The expression can be any mathematical expression using the standard operators (+, -, *, /, ^), parentheses, signed floating point numbers, imaginary numbers written as a number immediately followed by `i` (e.g. `1i`, `0.5i`; a bare `i` is a variable name), the functions `log(…)` (natural log) and `exp(…)`, other variable names, and coords (e.g. `y`, `t`, or a `--fit` coefficient; a variable of the same name takes precedence). A name may be scoped to another prefix as `prepath::key` (similar to `--with`).",
)
def parse_derive(arg: str) -> Derive:
    return Derive(arg)
