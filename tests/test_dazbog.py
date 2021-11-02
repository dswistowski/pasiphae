from os import listdir
from pathlib import Path

import pytest
from click.testing import CliRunner

from dazbog.cli import dazbog

examples_dir = Path(__file__).parent / "examples"


@pytest.mark.parametrize("path", listdir(examples_dir))
def test_from_directories(path):
    schema_path = examples_dir / path / "schema.graphql"
    resolvers_path = examples_dir / path / "expected-resolvers.py"
    expected_types_path = resolvers_path = examples_dir / path / "expected-types.py"
    types_path = resolvers_path = examples_dir / path / "types.py"
    runner = CliRunner()
    result = runner.invoke(
        dazbog, [str(schema_path)]
    )
    assert result.exception is None

    assert open(expected_types_path).read() == open(types_path).read()
