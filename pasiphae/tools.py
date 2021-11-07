import itertools as it
import operator
import re
import typing as t
from functools import singledispatch

from graphql import DocumentNode
from graphql.language import ast

from pasiphae.domain import CodeBlock

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


def chain_generators(
    sequence: t.Sequence[
        t.Tuple[
            str, t.Callable[[DocumentNode, t.Mapping[str, str]], t.Iterator[CodeBlock]]
        ]
    ],
    schema: DocumentNode,
) -> t.Iterator[t.Tuple[str, t.Iterator[CodeBlock]]]:
    known_types: t.Mapping[str, str] = {}
    for name, generator in sequence:
        codeblocks, for_imports = it.tee(generator(schema, known_types), 2)
        yield name, codeblocks
        all_python_types = it.chain(
            *map(operator.attrgetter("used_types"), for_imports)
        )
        all_import = filter(
            lambda import_: import_.module == f".{name}",
            it.chain(*map(operator.methodcaller("imports"), all_python_types)),
        )
        known_types = {
            **known_types,
            **{
                python_type.name: python_type.module
                for python_type in filter(
                    lambda python_type: python_type.module == f".{name}", all_import
                )
            },
        }
