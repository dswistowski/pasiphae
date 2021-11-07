from pathlib import Path

from ariadne import load_schema_from_path
from ariadne import make_executable_schema
from ariadne.asgi import GraphQL

from .resolvers import resolvers

type_defs = load_schema_from_path(Path(__file__).parent / "schema.graphql")

schema = make_executable_schema(type_defs, resolvers)
app = GraphQL(schema, debug=True)
