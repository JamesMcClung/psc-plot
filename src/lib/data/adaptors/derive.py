from lark import Lark
from lark.visitors import Transformer_InPlace

from lib import var_info_registry
from lib.data.adaptor import WorldAdaptor
from lib.data.data_world import DataWorld
from lib.data.ensure_derived import ensure_derived
from lib.data.loader import load
from lib.file_util import split_prepath
from lib.parsing.args_registry import arg_parser


class Derive(WorldAdaptor):
    def __init__(self, expression: str):
        self.expression = expression
        self.ast = _DERIVE_PARSER.parse(expression)

    def apply_world(self, world):
        return AssignNewVariable(world).transform(self.ast)

    def get_name_fragments(self):
        return [f'derive_"{self.expression}"']


class AssignNewVariable(Transformer_InPlace):
    def __init__(self, world: DataWorld):
        self.world = world
        super().__init__(visit_tokens=True)

    def number(self, toks: list):
        [tok] = toks
        return float(tok)

    def new_variable(self, toks: list):
        [tok] = toks
        return str(tok)

    def variable(self, toks: list):
        key = str(toks[0])
        data = self.world.require_active_data()
        data = ensure_derived(data, key)
        return data[key]

    def prepath(self, toks: list):
        return "/".join(str(tok) for tok in toks)

    def scoped_variable(self, toks: list):
        [prepath, key] = [str(tok) for tok in toks]
        if prepath not in self.world.datas:
            data = load(self.world.config, prepath)
        else:
            data = self.world.datas[prepath]

        data = ensure_derived(data, key)
        self.world = self.world.with_data(prepath, data)

        return data[key]

    def addition(self, toks: list):
        [lhs, rhs] = toks
        return lhs + rhs

    def subtraction(self, toks: list):
        [lhs, rhs] = toks
        return lhs - rhs

    def multiplication(self, toks: list):
        [lhs, rhs] = toks
        return lhs * rhs

    def division(self, toks: list):
        [lhs, rhs] = toks
        return lhs / rhs

    def exponentiation(self, toks: list):
        [lhs, rhs] = toks
        return lhs**rhs

    def assignment(self, toks: list):
        [key, subdata] = toks
        data = self.world.require_active_data()
        _, prefix = split_prepath(data.metadata.prepath)
        info = var_info_registry.lookup(prefix, key)
        data = data.with_active(data=subdata, key=key, info=info)
        return self.world.with_active(data=data)


_DERIVE_GRAMMAR = r"""
?start : assignment

assignment   : new_variable "=" expression
new_variable : CNAME

?expression : _expression_3

_expression_0 : "(" expression ")"
              | variable
              | scoped_variable
              | number
_expression_1 : _expression_0
              | exponentiation
_expression_2 : _expression_1
              | multiplication
              | division
_expression_3 : _expression_2
              | addition
              | subtraction

exponentiation : _expression_1 "^" _expression_0
multiplication : _expression_2 "*" _expression_1
division       : _expression_2 "/" _expression_1
addition       : _expression_3 "+" _expression_2
subtraction    : _expression_3 "-" _expression_2

variable        : CNAME
scoped_variable : prepath "::" CNAME
number          : SIGNED_NUMBER

prepath : PREFIX
# DIR    : /[^\/]+/ TODO figure out a way to make dirs work; as is, the arbitrary chars are incompatible with math symbols, especially /
PREFIX : /[.\w\d]+/

%import common.SIGNED_NUMBER
%import common.CNAME
%import common.WS
%ignore WS
"""


_DERIVE_PARSER = Lark(_DERIVE_GRAMMAR)
_DERIVE_FORMAT = "new_var_key=expression"


@arg_parser(
    dest="adaptors",
    flags="--derive",
    metavar=_DERIVE_FORMAT,
    help=f"Create a new variable with the given name. The expression can be any mathematical expression using the standard operators (+, -, *, /, ^), parentheses, signed floating point numbers, and other variable names. A name may be scoped to another prefix as `prepath::key` (similar to `--with`).",
)
def parse_derive(arg: str) -> Derive:
    return Derive(arg)
