from pathlib import Path

import click
from graphql import GraphQLSyntaxError
from graphql import parse

from pasiphae.types import generate_types


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

    types = "\n".join(generate_types(parsed_schema))
    types_file = schema.parent / "types.py"
    with open(types_file, "w") as f:
        f.write(types)
