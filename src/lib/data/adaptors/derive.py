from lib.data.adaptor import WorldAdaptor
from lib.data.data_world import DataWorld
from lib.data.ensure_derived import ensure_derived
from lib.data.expression import EXPRESSION_PARSER, ExpressionEvaluator, evaluate
from lib.data.loader import load
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
        data = self.world.require_active_data()
        data = ensure_derived(data, key, self.world.config)
        return data[key]

    def scoped_variable(self, toks: list):
        [prepath, key] = [str(tok) for tok in toks]
        if prepath not in self.world.datas:
            data = load(self.world.config, prepath)
        else:
            data = self.world.datas[prepath]

        data = ensure_derived(data, key, self.world.config)
        self.world = self.world.with_data(prepath, data)

        return data[key]

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
    help=f"Create a new variable with the given name. The expression can be any mathematical expression using the standard operators (+, -, *, /, ^), parentheses, signed floating point numbers, imaginary numbers written as a number immediately followed by `i` (e.g. `1i`, `0.5i`; a bare `i` is a variable name), and other variable names. A name may be scoped to another prefix as `prepath::key` (similar to `--with`).",
)
def parse_derive(arg: str) -> Derive:
    return Derive(arg)
