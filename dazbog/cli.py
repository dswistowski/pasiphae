from pathlib import Path
from typing import IO
import itertools as it
import click
from graphql import GraphQLSyntaxError
from graphql import parse

from dazbog.types import generate_types


@click.command()
@click.argument("schema", type=click.Path(path_type=Path))
@click.option("--debug/--no-debug", default=False)
def dazbog(schema: Path, debug: bool):
    """Generate TYPES and update RESOLVERS from SCHEMA

    SCHEMA is path to source graphql schema
    """
    with open(schema) as f:
        schema_data = f.read()
    try:
        parsed_schema = parse(schema_data)
    except GraphQLSyntaxError as e:
        click.echo(f"Failed to parse schema - {e}")
        if debug:
            raise
        raise SystemExit(1)

    types = '\n'.join(generate_types(parsed_schema))
    types_file = schema.parent / "types.py"
    with open(types_file, "w") as f:
        f.write(types)
