import re
import typing as t

CAMEL_RE_PRE = re.compile("(.)([A-Z][a-z]+)")
CAMEL_RE_POST = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    name = CAMEL_RE_PRE.sub(r"\1_\2", name)
    return CAMEL_RE_POST.sub(r"\1_\2", name).lower()


T = t.TypeVar("T")


def with_last(items: t.Sequence[T]) -> t.Iterator[t.Tuple[T, bool]]:
    prev: T
    is_first = True
    for current in items:
        if is_first:
            is_first = False
        else:
            yield prev, False
        prev = current
    if not is_first:
        yield prev, True
