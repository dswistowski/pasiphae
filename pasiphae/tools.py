import re
import typing as t
from functools import singledispatch

from graphql.language import ast

CAMEL_RE_PRE = re.compile("(.)([A-Z][a-z]+)")
CAMEL_RE_POST = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    name = CAMEL_RE_PRE.sub(r"\1_\2", name)
    return CAMEL_RE_POST.sub(r"\1_\2", name).lower()


@singledispatch
def has_arguments(
    _field: t.Union[ast.FieldDefinitionNode, ast.InputValueDefinitionNode]
) -> bool:
    raise RuntimeError()


@has_arguments.register
def field_has_arguments(field: ast.FieldDefinitionNode) -> bool:
    return bool(field.arguments)


@has_arguments.register
def input_has_arguments(_field: ast.InputValueDefinitionNode) -> bool:
    return False
