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
    types_path = resolvers_path = examples_dir / path / "expected-types.py"
    runner = CliRunner()
    result = runner.invoke(
        dazbog, [str(schema_path), str(resolvers_path), str(types_path)]
    )
    assert result.exception is None
