import dataclasses as d
import itertools as it
import operator
import typing as t
from enum import Enum
from functools import partial
from functools import singledispatch

from graphql import DocumentNode
from graphql.language import ast

from .domain import CodeBlock
from .domain import PythonType
from .to_python_type import to_python_type
from .tools import camel_to_snake
from .tools import has_arguments

MODULE = ".resolvers"


class ResolverType(Enum):
    OBJECT_TYPE = "ObjectType"
    ENUM_TYPE = "EnumType"
    QUERY_TYPE = "QueryType"
    MUTATION_TYPE = "MutationType"


@d.dataclass(frozen=True)
class Value:
    value: str
    type_: PythonType


@d.dataclass
class ResolverFunctionArgument:
    schema_name: str
    type_: PythonType
    default: t.Optional[Value]

    @property
    def types(self) -> t.Iterator[PythonType]:
        yield self.type_

    @property
    def name(self) -> str:
        return camel_to_snake(self.schema_name)

    def __str__(self) -> str:
        default = f" = {self.default.value}" if self.default else ""
        return f"{self.name}: {self.type_.render(MODULE)}{default}"


@d.dataclass
class ResolverFunction:
    schema_name: str
    return_: PythonType
    arguments: t.Sequence[ResolverFunctionArgument] = d.field(default_factory=list)

    @property
    def types(self) -> t.Iterator[PythonType]:
        yield PythonType("GraphQLResolveInfo", module="graphql")
        yield from it.chain(*map(operator.attrgetter("types"), self.arguments))
        yield self.return_

    def render(self, resolver: "ObjectResolver") -> str:
        first = (
            f"{resolver.name}_: {resolver.parent.render(MODULE)}"
            if resolver.parent
            else "_: None"
        )
        arguments = (
            f"{first}, info: GraphQLResolveInfo, {', '.join(map(str, self.arguments))}"
        )
        result = self.return_.render(MODULE)

        head = f"def resolve_{resolver.name}_{self.name}({arguments}) -> {result}:"
        body = "    ..."
        return f"{head}\n{body}"

    @property
    def name(self) -> str:
        return camel_to_snake(self.schema_name)


@d.dataclass
class Resolver:
    schema_name: str
    type_: ResolverType

    @property
    def name(self) -> str:
        return camel_to_snake(self.schema_name)

    def to_codeblock(self) -> CodeBlock:
        return CodeBlock(body=self.body, used_types=list(self.types))

    @property
    def body(self):
        return f'{self.name} = {self.type_.value}("{self.schema_name}")'

    @property
    def types(self) -> t.Iterator[PythonType]:
        yield PythonType(self.type_.value, module="ariadne")


@d.dataclass
class ObjectResolver(Resolver):
    parent: t.Optional[PythonType]
    functions: t.Sequence[ResolverFunction] = d.field(default_factory=list)

    @property
    def types(self) -> t.Iterator[PythonType]:
        yield from super().types

        yield from it.chain(*map(operator.attrgetter("types"), self.functions))

    def generator(self) -> t.Iterator[str]:
        if not self.parent:
            yield f"{self.name} = {self.type_.value}()"
        else:
            yield super().body
        for function in self.functions:
            yield f'@{self.name}.field("{function.schema_name}")'
            yield function.render(resolver=self)

    @property
    def body(self) -> str:
        return "\n".join(self.generator())


@d.dataclass
class EnumResolver(Resolver):
    target: PythonType

    type_: t.Literal[ResolverType.ENUM_TYPE]

    @property
    def body(self):
        arguments = f'"{self.schema_name}", values={self.target.name}'
        return f"{self.name} = {self.type_.value}({arguments})"

    @property
    def types(self) -> t.Iterator[PythonType]:
        yield from super().types
        yield self.target


def generate_resolvers(
    root: DocumentNode, known_types: t.Mapping[str, str]
) -> t.Iterator[CodeBlock]:
    all_resolvers = list(
        filter(
            None,
            map(partial(process_definition, known_types=known_types), root.definitions),
        )
    )
    if all_resolvers:
        yield from map(operator.methodcaller("to_codeblock"), all_resolvers)
        resolvers = ",".join(map(operator.attrgetter("name"), all_resolvers))
        yield CodeBlock(body=f"resolvers = [{resolvers}]")


@singledispatch
def process_definition(
    definition: ast.DefinitionNode, known_types: t.Mapping[str, str]
) -> t.Optional[Resolver]:
    raise NotImplementedError(f"Cannot process {definition.__class__}")


object_type_overrides: t.Mapping[str, ResolverType] = {
    "Query": ResolverType.QUERY_TYPE,
    "Mutation": ResolverType.MUTATION_TYPE,
}


@process_definition.register(ast.SchemaDefinitionNode)
@process_definition.register(ast.DirectiveDefinitionNode)
def do_not_processed(
    definition: ast.DefinitionNode, known_types: t.Mapping[str, str]
) -> None:
    return None


@process_definition.register(ast.ObjectTypeDefinitionNode)
def process_object(
    definition: ast.ObjectTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> Resolver:
    definition_name = definition.name.value
    type_ = object_type_overrides.get(definition_name, ResolverType.OBJECT_TYPE)

    functions = map(
        partial(resolver_function, known_types=known_types),
        filter(has_arguments, definition.fields),
    )
    parent = (
        None
        if type_ in {ResolverType.QUERY_TYPE, ResolverType.MUTATION_TYPE}
        else PythonType(definition_name, known_types[definition_name])
    )

    return ObjectResolver(
        schema_name=definition_name,
        type_=type_,
        functions=list(functions),
        parent=parent,
    )


@process_definition.register
def process_interface(
    definition: ast.InterfaceTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> t.Optional[Resolver]:
    # TODO: create interface processor
    return None


@process_definition.register
def process_input(
    definition: ast.InputObjectTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> t.Optional[Resolver]:
    # TODO: create input processor
    return None


@process_definition.register
def process_union(
    definition: ast.UnionTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> t.Optional[Resolver]:
    # TODO: create union processor
    return None


@process_definition.register
def process_scalar(
    defiinition: ast.ScalarTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> t.Optional[Resolver]:
    # TODO: create scalar processor
    return None


@process_definition.register
def process_enum(
    definition: ast.EnumTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> t.Optional[Resolver]:
    definition_name = definition.name.value
    return EnumResolver(
        schema_name=definition_name,
        type_=ResolverType.ENUM_TYPE,
        target=PythonType(definition_name, module=".types"),
    )


def resolver_function(
    field: ast.FieldDefinitionNode, known_types: t.Mapping[str, str]
) -> ResolverFunction:
    return ResolverFunction(
        schema_name=field.name.value,
        return_=to_python_type(field.type, known_types),
        arguments=list(
            map(
                partial(to_resolve_function_argument, known_types=known_types),
                field.arguments,
            )
        ),
    )


def to_resolve_function_argument(
    argument: ast.InputValueDefinitionNode, known_types: t.Mapping[str, str]
) -> ResolverFunctionArgument:

    type_ = to_python_type(argument.type, known=known_types)
    if argument.default_value:
        type_ = type_.child[0]

    return ResolverFunctionArgument(
        schema_name=argument.name.value,
        default=to_value(argument.default_value, type_=type_),
        type_=type_,
    )


@singledispatch
def to_value(value: t.Optional[ast.ValueNode], type_: PythonType) -> t.Optional[Value]:
    raise NotImplementedError(f"do not know {value.__class__.__name__} yet")


@to_value.register
def none_to_value(_: None, type_: PythonType) -> t.Optional[Value]:
    return None


@to_value.register
def enum_to_value(value: ast.EnumValueNode, type_: PythonType) -> t.Optional[Value]:
    return Value(value=f"{type_.name}.{value.value}", type_=type_)
