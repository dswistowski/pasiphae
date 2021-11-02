from pathlib import Path
from typing import IO

import click
from graphql import GraphQLSyntaxError
from graphql import parse

from dazbog.types import generate_types


@click.command()
@click.argument("schema", type=click.File("rt"))
@click.argument("types", type=click.Path())
@click.argument("resolvers", type=click.Path())
@click.option("--debug/--no-debug", default=False)
def dazbog(schema: IO[str], types: Path, resolvers: Path, debug: bool) -> int:
    """Generate TYPES and update RESOLVERS from SCHEMA

    SCHEMA is path to source graphql schema
    TYPES is path to result expected-types.py module
    RESOLVERS is path to result resolvers module
    """
    try:
        parsed_schema = parse(schema.read())
    except GraphQLSyntaxError as e:
        click.echo(f"Failed to parse schema - {e}")
        if debug:
            raise
        raise SystemExit(1)

    # types = "\n".join(generate_types(parsed_schema))
    for line in generate_types(parsed_schema):
        print(line)
    # print(types)
