from dataclasses import dataclass, field, replace
from functools import singledispatch
import typing as t

from graphql import DocumentNode
from graphql.language import ast


@dataclass
class PythonType:
    name: str
    import_: t.Optional[str] = None
    required: bool = False

    def __str__(self) -> str:
        if not self.required:
            return f"t.Optional[{self.name}]"
        return self.name


build_in_types: t.Mapping[str, PythonType] = {
    'ID': PythonType('UUID', 'uuid'),
    'String': PythonType('str'),
    'Float': PythonType('Decimal', 'decimal'),
    'Int': PythonType('int'),
    'Boolean': PythonType('bool')
}


def generate_types(root: DocumentNode) -> t.Iterator[str]:
    defined_types = {
        definition.name.value for definition in root.definitions
    }

    definitions = [process_definition(definition, defined_types) for definition in root.definitions]

    for definition in definitions:
        if definition:
            yield definition.body
            yield ""
            yield ""


@dataclass
class TypedDefinition:
    body: str
    used_types: t.Sequence[PythonType] = field(default_factory=list)


@singledispatch
def process_definition(definition: ast.DefinitionNode, defined_types: t.Set[str]) -> TypedDefinition:
    ...
    # raise NotImplementedError(f"Cannot process {definition.__class__}")


@process_definition.register
def process_object(object: ast.ObjectTypeDefinitionNode, defined_types: t.Set[str]) -> t.Iterator[str]:
    if object.name.value not in {'Query', 'Mutation'}:
        yield f"class {object.name.value}:"
        for field in object.fields:
            process_result = type_node(field.type, defined_types)
            yield f"    {field.name.value}: {process_result}"
        yield ""
        yield ""


@process_definition.register
def process_enum(enum: ast.EnumTypeDefinitionNode, defined_types: t.Set[str]) -> t.Iterator[str]:
    yield f"class {enum.name.value}(Enum)"
    for field in enum.values:
        yield f'    {field.name.value} = "{field.name.value}"'
    yield ''
    yield ''



@singledispatch
def type_node(node: ast.TypeNode, defined_types: t.Set[str]) -> PythonType:
    raise NotImplementedError(f"Not implemented {node.__class__}")


@type_node.register
def named_type_mode(named_type_node: ast.NamedTypeNode, defined_types: t.Set[str]) -> PythonType:
    name = named_type_node.name.value
    if name in defined_types:
        return PythonType(
            f"'{name}'"
        )
    try:
        return build_in_types[name]
    except KeyError:
        raise NotImplementedError(f"do not know {name}")


@type_node.register
def not_null_type_node(not_null_type_node: ast.NonNullTypeNode, defined_types: t.Set[str]) -> PythonType:
    processed = type_node(not_null_type_node.type, defined_types)
    return replace(processed, required=True)


@type_node.register
def list_type_node(list_type_node: ast.ListTypeNode, defined_types: t.Set[str]) -> PythonType:
    processed = type_node(list_type_node.type, defined_types)
    return replace(processed, name=f"t.Sequence[{processed}]", required=False)