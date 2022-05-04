from os import listdir
from pathlib import Path

import pytest
from click.testing import CliRunner

from pasiphae.cli import pasiphae

examples_dir = Path(__file__).parent / "examples"

FILES_TO_IGNORE = {"out"}


@pytest.mark.parametrize("path", listdir(examples_dir))
def test_from_directories(path):
    in_path = examples_dir / path / "in"
    out_path = examples_dir / path / "out"

    schema_path = in_path / "schema.graphql"
    runner = CliRunner()
    result = runner.invoke(
        pasiphae, [str(schema_path), "--app"], catch_exceptions=False
    )
    assert result.exception is None

    assert listdir(in_path) == listdir(
        out_path
    ), "in and out dirs content should be the same"
    for file_name in listdir(in_path):
        assert (
            open(in_path / file_name).read() == open(out_path / file_name).read()
        ), f"{file_name} should be the same in in and out"
