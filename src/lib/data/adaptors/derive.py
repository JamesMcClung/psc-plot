from lark import Lark
from lark.visitors import Transformer_InPlace

from lib import var_info_registry
from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import Field, List
from lib.data.loader import get_loader
from lib.derived_field_variables.derived_field_variable import (
    DERIVED_FIELD_VARIABLES,
    derive_field_variable,
)
from lib.derived_particle_variables.derived_particle_variable import (
    derive_particle_variable,
)
from lib.parsing.args_registry import arg_parser


class Derive(WorldAdaptor):
    def __init__(self, expression: str):
        self.expression = expression
        self.ast = _DERIVE_PARSER.parse(expression)

    def apply_world(self, world):
        active = world.active_data
        scoped_prefixes = _collect_scoped_prefixes(self.ast)

        if isinstance(active, List):
            if scoped_prefixes:
                raise ValueError("--derive: cross-prefix references (prefix::key) are not supported for particle data.")
            return world.with_active_data(AssignNewVariable(active).transform(self.ast))

        if isinstance(active, Field):
            siblings = _load_siblings(world, scoped_prefixes)
            return world.with_active_data(AssignNewFieldVariable(active, siblings).transform(self.ast))

        raise ValueError("--derive requires an active variable to derive into; specify one as a positional argument.")

    def get_name_fragments(self):
        if self.ast.data == "assign_default":
            return []
        return [f'derive_"{self.expression}"']


def _collect_scoped_prefixes(ast) -> set[str]:
    """Distinct prefixes referenced via `prefix::key` anywhere in the expression."""
    prefixes = set()
    for tree in ast.find_data("variable"):
        if len(tree.children) == 2:
            prefixes.add(str(tree.children[0]))
    return prefixes


def _load_siblings(world, prefixes: set[str]) -> dict[str, Field]:
    """Resolve each scoped prefix to a loaded Field, reusing any already in the world
    and auto-loading the rest the same way `--with` does."""
    siblings: dict[str, Field] = {}
    for prefix in prefixes:
        if prefix in world.datas:
            siblings[prefix] = world.datas[prefix]
        else:
            loaded = get_loader(world.config.data_dir, prefix, None).apply_world(world)
            siblings[prefix] = loaded.datas[prefix]
    return siblings


def _resolve_field_variable(field: Field, key: str) -> Field:
    """Return a Field guaranteed to contain `key`, deriving it via the prefix's
    registry when it isn't already in the dataset."""
    if key in field.data:
        return field
    prefix = field.metadata.prefix
    if prefix is None:
        raise ValueError(f"--derive cannot resolve '{key}': field metadata has no prefix.")
    if key not in DERIVED_FIELD_VARIABLES.get(prefix, {}):
        raise ValueError(
            f"--derive: '{key}' is not in the '{prefix}' dataset and not in its derived-variable registry {list(DERIVED_FIELD_VARIABLES.get(prefix, {}))}. Note that earlier adaptors (e.g. --downsample) may have dropped variables that became incompatible with the active grid; consider moving --derive earlier in the pipeline."
        )
    return derive_field_variable(field, key, prefix)


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
    def __init__(self, data: Field, siblings: dict[str, Field]):
        self._data = data
        self._siblings = siblings
        super().__init__(visit_tokens=True)

    def number(self, toks: list):
        [tok] = toks
        return float(tok)

    def new_variable(self, toks: list):
        [tok] = toks
        return str(tok)

    def variable(self, toks: list):
        if len(toks) == 2:
            prefix, key = str(toks[0]), str(toks[1])
            sibling = _resolve_field_variable(self._siblings[prefix], key)
            self._siblings[prefix] = sibling
            return sibling.data[key]
        key = str(toks[0])
        self._data = _resolve_field_variable(self._data, key)
        return self._data.data[key]

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
        self._data = _resolve_field_variable(self._data, new_variable)
        dim = var_info_registry.lookup(self._data.metadata.prefix, new_variable)
        new_var_infos = {**self._data.metadata.var_infos, new_variable: dim}
        return self._data.assign_metadata(active_key=new_variable, var_infos=new_var_infos)

    def assignment(self, toks: list):
        [new_variable, val] = toks
        new_ds = self._data.data | {new_variable: val}
        dim = var_info_registry.lookup(self._data.metadata.prefix, new_variable)
        new_var_infos = {**self._data.metadata.var_infos, new_variable: dim}
        return self._data.assign(new_ds, active_key=new_variable, var_infos=new_var_infos)


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

variable : (CNAME "::")? CNAME
number   : SIGNED_NUMBER

%import common.SIGNED_NUMBER
%import common.CNAME
%import common.WS
%ignore WS
"""


_DERIVE_PARSER = Lark(_DERIVE_GRAMMAR)

_DERIVE_FORMAT = "new_var_key[=expression]"
_EXPRESSION_DESCRIPTION = "The expression can be any mathematical expression using the standard operators (+, -, *, /, ^), parentheses, signed floating point numbers, and existing variable names. A name may be scoped to another prefix as prefix::key (that prefix is auto-loaded)."


@arg_parser(
    dest="adaptors",
    flags="--derive",
    metavar=_DERIVE_FORMAT,
    help=f"Create a new variable with the given name. {_EXPRESSION_DESCRIPTION} If the expression is omitted, the variable is derived via the registry of derivable variables.",
)
def parse_derive(arg: str) -> Derive:
    return Derive(arg)
