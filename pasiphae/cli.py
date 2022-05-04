from pathlib import Path

import click
import graphql
import itertools as it

from . import file
from .resolvers import generate_resolvers
from .tools import chain_generators
from .types import generate_types

APP = """from pathlib import Path
from ariadne import load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL
from .resolvers import resolvers

type_defs = load_schema_from_path(Path(__file__).parent / "{schema_name}")

schema = make_executable_schema(type_defs, resolvers)
app = GraphQL(schema, debug=True)
"""


@click.command()
@click.argument("schema", type=click.Path(path_type=Path))
@click.option("--debug/--no-debug", default=False)
@click.option("--app", default=False, is_flag=True)
def pasiphae(schema: Path, debug: bool, app: bool) -> None:
    """Generate ariadne service from provided schema"""
    with open(schema) as f:
        schema_data = f.read()
    try:
        parsed_schema = graphql.parse(schema_data)
    except graphql.GraphQLSyntaxError as e:
        click.echo(f"Failed to parse schema - {e}")
        if debug:
            raise
        raise SystemExit(1)

    for name, codeblocks in chain_generators(
        [("types", generate_types), ("resolvers", generate_resolvers)], parsed_schema
    ):
        codeblocks, for_errors = it.tee(codeblocks)

        file.write(schema.parent, name, codeblocks)
        for codeblock in for_errors:
            if codeblock.warning:
                click.echo(f"⚠️  {codeblock.warning}")

    if app:
        with open(schema.parent / "app.py", "w") as f:
            f.write(APP.format(schema_name=schema.name))
        file.reformat_file(schema.parent / "app.py")

    (schema.parent / "__init__.py").touch(exist_ok=True)
