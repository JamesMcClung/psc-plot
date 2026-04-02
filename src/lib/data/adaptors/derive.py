from lark import Lark
from lark.visitors import Transformer_InPlace

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import List
from lib.derived_particle_variables.derived_particle_variable import (
    derive_particle_variable,
)
from lib.parsing.args_registry import arg_parser


class Derive(MetadataAdaptor):
    def __init__(self, expression: str):
        self.expression = expression
        self.ast = _DERIVE_PARSER.parse(expression)

    def apply_list(self, data: List) -> List:
        return AssignNewVariable(data).transform(self.ast)

    def get_name_fragments(self):
        if self.ast.data == "assign_default":
            return []
        return [f'derive_"{self.expression}"']


class AssignNewVariable(Transformer_InPlace):
    def __init__(self, data: List):
        self._data = data
        super().__init__(visit_tokens=True)

    def number(self, toks: list):
        [tok] = toks
        return float(tok)

    def new_variable(self, toks: list):
        [tok] = toks
        return tok

    def variable(self, toks: list):
        [tok] = toks
        return self._data.data[tok]

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

    def assign_default(self, toks: list):
        [new_variable] = toks
        return derive_particle_variable(self._data, new_variable, "prt")

    def assignment(self, toks: list):
        [new_variable, val] = toks
        df = self._data.data
        df = df.assign(**{new_variable: val})
        return self._data.assign_data(df)


_DERIVE_GRAMMAR = r"""
?start : assign_default | assignment

assign_default : new_variable
assignment     : new_variable "=" expression
new_variable   : CNAME

?expression : _expression_3

_expression_0 : "(" expression ")"
              | variable
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

variable : CNAME
number   : SIGNED_NUMBER

%import common.SIGNED_NUMBER
%import common.CNAME
%import common.WS
%ignore WS
"""


_DERIVE_PARSER = Lark(_DERIVE_GRAMMAR)

_DERIVE_FORMAT = "var_name[=expression]"
_EXPRESSION_DESCRIPTION = "The expression can be any mathematical expression using the standard operators (+, -, *, /, ^), parentheses, signed floating point numbers, and existing variable names."


@arg_parser(
    dest="adaptors",
    flags="--derive",
    metavar=_DERIVE_FORMAT,
    help=f"Create a new variable with the given name. {_EXPRESSION_DESCRIPTION} If the expression is omitted, the variable name is derived via the registry of derivable variables.",
)
def parse_derive(arg: str) -> Derive:
    return Derive(arg)
