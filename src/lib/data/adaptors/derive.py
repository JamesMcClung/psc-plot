from lark import Lark
from lark.visitors import Transformer_InPlace

from lib import field_units
from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, List
from lib.derived_field_variables.derived_field_variable import (
    DERIVED_FIELD_VARIABLES,
    derive_field_variable,
)
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

    def apply_field(self, data: Field) -> Field:
        return AssignNewFieldVariable(data).transform(self.ast)

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


class AssignNewFieldVariable(Transformer_InPlace):
    def __init__(self, data: Field):
        self._data = data
        super().__init__(visit_tokens=True)

    def number(self, toks: list):
        [tok] = toks
        return float(tok)

    def new_variable(self, toks: list):
        [tok] = toks
        return str(tok)

    def variable(self, toks: list):
        [tok] = toks
        name = str(tok)
        ds = self._data.data
        if name not in ds.variables:
            self._resolve_from_registry(name)
        return self._data.data[name]

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
        self._resolve_from_registry(new_variable)
        dim = field_units.lookup(self._data.metadata.prefix, new_variable)
        new_var_info = {**self._data.metadata.var_info, new_variable: dim}
        return self._data.assign_metadata(var_name=new_variable, display_latex=dim.name.latex, unit_latex=dim.unit.latex, var_info=new_var_info)

    def assignment(self, toks: list):
        [new_variable, val] = toks
        new_ds = self._data.data.assign({new_variable: val})
        dim = field_units.lookup(self._data.metadata.prefix, new_variable)
        new_var_info = {**self._data.metadata.var_info, new_variable: dim}
        return self._data.assign(new_ds, var_name=new_variable, display_latex=dim.name.latex, unit_latex=dim.unit.latex, var_info=new_var_info)

    def _resolve_from_registry(self, name: str):
        prefix = self._data.metadata.prefix
        if prefix is None:
            raise ValueError(f"--derive cannot resolve '{name}': field metadata has no prefix.")
        if name not in DERIVED_FIELD_VARIABLES.get(prefix, {}):
            raise ValueError(
                f"--derive: '{name}' is not in the dataset and not in the registry for prefix '{prefix}'. "
                f"Note that earlier adaptors (e.g. --downsample) may have dropped variables that became "
                f"incompatible with the active grid; consider moving --derive earlier in the pipeline."
            )
        # Mutates self._data.data in-place to add `name` (and any of its dependencies).
        derive_field_variable(self._data.data, name, prefix)


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
