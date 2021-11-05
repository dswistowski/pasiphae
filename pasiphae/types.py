import operator
import typing as t
from functools import singledispatch

from graphql import DocumentNode
from graphql.language import ast

from .domain import CodeBlock
from .domain import PythonType
from .to_python_type import named_type_mode
from .to_python_type import to_python_type
from .tools import camel_to_snake
from .tools import has_arguments

UNION_WEIGHT, ENUM_WEIGHT, PROTOCOL_WEIGHT, DEFAULT_WEIGHT = range(4)


MODULE = ".types"


render_type = operator.methodcaller("render", module=MODULE)


@singledispatch
def get_name_node(node: ast.DefinitionNode) -> t.Optional[ast.NameNode]:
    raise NotImplementedError(f"Should never process not node: {node}")


@get_name_node.register(ast.ExecutableDefinitionNode)
@get_name_node.register(ast.TypeDefinitionNode)
def get_name_node_(
    node: t.Union[ast.ExecutableDefinitionNode, ast.TypeDefinitionNode]
) -> t.Optional[ast.NameNode]:
    return node.name


def generate_types(
    root: DocumentNode, known_types: t.Mapping[str, str]
) -> t.Iterator[CodeBlock]:
    known_types = {
        **known_types,
        **{
            definition.value: MODULE
            for definition in filter(
                None, (get_name_node(definition) for definition in root.definitions)
            )
        },
    }

    return filter(
        None,
        (
            process_definition(definition, known_types)
            for definition in root.definitions
        ),
    )


@singledispatch
def process_definition(
    definition: ast.DefinitionNode, _known_types: t.Mapping[str, str]
) -> t.Optional[CodeBlock]:
    raise NotImplementedError(f"Cannot process {definition.__class__}")


@singledispatch
def get_interfaces(
    _definition: t.Union[
        ast.ObjectTypeDefinitionNode, ast.InputObjectTypeDefinitionNode
    ]
) -> str:
    return ""


@get_interfaces.register
def get_interfaces_object(definition: ast.ObjectTypeDefinitionNode) -> str:
    return ", ".join(map(lambda type_: type_.name.value, definition.interfaces))


@process_definition.register(ast.ObjectTypeDefinitionNode)
@process_definition.register(ast.InputObjectTypeDefinitionNode)
def process_object(
    definition: t.Union[
        ast.ObjectTypeDefinitionNode, ast.InputObjectTypeDefinitionNode
    ],
    known_types: t.Mapping[str, str],
) -> t.Optional[CodeBlock]:
    if definition.name.value in ("Query", "Mutation"):
        return None

    if interfaces := get_interfaces(definition):
        interfaces = f"({interfaces})"

    return process_interface_or_object(
        definition,
        known_types,
        header=(
            "@dataclass(frozen=True)",
            f"class {definition.name.value}{interfaces}:",
        ),
        weight=DEFAULT_WEIGHT,
        type_=PythonType("dataclass", "dataclasses"),
    )


@process_definition.register
def proess_interface(
    definition: ast.InterfaceTypeDefinitionNode, known_types: t.Mapping[str, str]
) -> CodeBlock:
    return process_interface_or_object(
        definition,
        known_types,
        header=(f"class {definition.name.value}(Protocol):",),
        weight=PROTOCOL_WEIGHT,
        type_=PythonType("Protocol", "typing"),
    )


def process_interface_or_object(
    definition: t.Union[
        ast.ObjectTypeDefinitionNode,
        ast.InputObjectTypeDefinitionNode,
        ast.InterfaceTypeDefinitionNode,
    ],
    known_types: t.Mapping[str, str],
    header: t.Sequence[str],
    weight: int,
    type_: PythonType,
) -> CodeBlock:

    process_results: t.Mapping[str, PythonType] = {
        field.name.value: to_python_type(field.type, known_types)
        for field in definition.fields
        if not has_arguments(field)
    }

    sorted_process_results = sorted(
        (
            (result.default, camel_to_snake(name), result.render(MODULE))
            for name, result in process_results.items()
        ),
        key=operator.itemgetter(0),
    )

    body = (
        *(header),
        *(
            f"    {name}: {result}{f' = {default}' if default else ''}"
            for default, name, result in sorted_process_results
        ),
    )
    return CodeBlock(
        body="\n".join(body),
        used_types=(
            *(result for result in process_results.values()),
            type_,
            PythonType(definition.name.value, module=MODULE),
        ),
        weight=weight,
    )


@process_definition.register
def process_enum(
    enum: ast.EnumTypeDefinitionNode, _defined_types: t.Set[str]
) -> CodeBlock:
    body = (
        f"class {enum.name.value}(Enum):",
        *(f'    {field.name.value} = "{field.name.value}"' for field in enum.values),
    )
    return CodeBlock(
        body="\n".join(body),
        used_types=[
            PythonType("Enum", "enum"),
            PythonType(enum.name.value, module=MODULE),
        ],
        weight=ENUM_WEIGHT,
    )


@process_definition.register
def process_union(
    union: ast.UnionTypeDefinitionNode, known: t.Mapping[str, str]
) -> CodeBlock:
    types = [
        named_type_mode(type_, known, optional=lambda x: x) for type_ in union.types
    ]
    return CodeBlock(
        body=f"{union.name.value} = Union[{', '.join(map(render_type, types))}]",
        used_types=[
            *types,
            PythonType("Union", "typing"),
            PythonType(union.name.value, module=MODULE),
        ],
        weight=UNION_WEIGHT,
    )
