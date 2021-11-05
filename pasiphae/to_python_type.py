import typing as t
from functools import singledispatch

from graphql.language import ast

from pasiphae.domain import PythonType

build_in_types: t.Mapping[str, PythonType] = {
    "ID": PythonType("UUID", "uuid"),
    "String": PythonType("str"),
    "Float": PythonType("Decimal", "decimal"),
    "Int": PythonType("int"),
    "Boolean": PythonType("bool"),
}


@singledispatch
def to_python_type(node: ast.TypeNode, known: t.Mapping[str, str]) -> PythonType:
    raise NotImplementedError(f"Not implemented {node.__class__}")


def optional(type_: PythonType) -> PythonType:
    return PythonType("Optional", child=[type_], module="typing", default="None")


@to_python_type.register
def named_type_mode(
    named_type_node: ast.NamedTypeNode,
    known: t.Mapping[str, str],
    optional: t.Callable[[PythonType], PythonType] = optional,
) -> PythonType:
    name = named_type_node.name.value
    try:
        return optional(PythonType(name, module=known[name]))
    except KeyError:
        pass
    try:
        return optional(build_in_types[name])
    except KeyError:
        raise NotImplementedError(f"do not know {name}")


@to_python_type.register
def not_null_type_node(
    node: ast.NonNullTypeNode, known: t.Mapping[str, str]
) -> PythonType:
    processed = to_python_type(node.type, known)
    assert processed.name == "Optional"
    return processed.child[0]


@to_python_type.register
def list_type_node(node: ast.ListTypeNode, known: t.Mapping[str, str]) -> PythonType:
    processed = to_python_type(node.type, known)
    return optional(PythonType("Sequence", module="typing", child=[processed]))
