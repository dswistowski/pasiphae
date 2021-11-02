# managed by dazbog, it's safe to change body of methods

from ariadne import QueryType
from graphql import GraphQLResolveInfo

query = QueryType()


@query.field("foo")
def query_resolve_field_foo(_: None, _info: GraphQLResolveInfo) -> str:
    raise NotImplementedError("Dazbog generated resolver")


resolvers = [
    query
]