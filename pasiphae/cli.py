import itertools as it
import operator
import typing as t
from pathlib import Path

import click
from graphql import DocumentNode
from graphql import GraphQLSyntaxError
from graphql import parse

from . import file
from .domain import CodeBlock
from .resolvers import generate_resolvers
from .types import generate_types


@click.command()
@click.argument("schema", type=click.Path(path_type=Path))
@click.option("--debug/--no-debug", default=False)
def pasiphae(schema: Path, debug: bool) -> None:
    """Generate ariadne service from provided schema"""
    with open(schema) as f:
        schema_data = f.read()
    try:
        parsed_schema = parse(schema_data)
    except GraphQLSyntaxError as e:
        click.echo(f"Failed to parse schema - {e}")
        if debug:
            raise
        raise SystemExit(1)

    for name, codeblocks in chain_generators(
        [("types", generate_types), ("resolvers", generate_resolvers)], parsed_schema
    ):
        file.write(schema.parent, name, codeblocks)


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
