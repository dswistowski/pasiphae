import dataclasses as d
import operator
import sys
import typing as t


@d.dataclass(frozen=True)
class Import:
    name: str
    module: str

    def __str__(self):
        return f"from {self.module} import {self.name}"


@d.dataclass(frozen=True)
class PythonType:
    name: str
    module: t.Optional[str] = None
    child: t.Sequence["PythonType"] = d.field(default_factory=list)
    default: str = ""

    def imports(self) -> t.Iterator[Import]:
        for type_ in self.traverse():
            if type_.module:
                yield Import(type_.name, type_.module)

    def traverse(self) -> t.Iterator["PythonType"]:
        yield self
        for child in self.child:
            yield from child.traverse()

    def render(self, module: str) -> str:
        if self.child:
            child = ", ".join(
                map(operator.methodcaller("render", module=module), self.child)
            )
            return f"{self.name}[{child}]"
        if module == self.module:
            return f'"{self.name}"'
        return self.name

    def __str__(self):
        raise NotImplementedError()


@d.dataclass(frozen=True)
class CodeBlock:
    body: str
    used_types: t.Sequence[PythonType] = d.field(default_factory=list)
    weight: int = sys.maxsize
