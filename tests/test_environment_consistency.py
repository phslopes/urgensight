"""Coerencia de versoes entre os ambientes do projeto.

O modelo e treinado no container do Airflow e servido pela API. Quando as
versoes de Python ou das bibliotecas que atravessam o pickle divergem entre
esses ambientes, a falha aparece so em runtime, ao desserializar
models/model.pkl. Estes testes transformam essa divergencia em erro de
suite.
"""

import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PYTHON_MAJOR_MINOR = "3.12"


def read_pyproject() -> dict:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text("utf-8"))


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text("utf-8")


class TestPythonFloor:
    def test_pyproject_requires_python_312(self):
        assert read_pyproject()["project"]["requires-python"] == ">=3.12"

    def test_ruff_targets_py312(self):
        assert read_pyproject()["tool"]["ruff"]["target-version"] == "py312"

    def test_python_version_file_matches_floor(self):
        assert read_text(".python-version").strip() == PYTHON_MAJOR_MINOR

    def test_api_dockerfile_uses_same_python(self):
        assert f"FROM python:{PYTHON_MAJOR_MINOR}-slim" in read_text("Dockerfile")

    def test_airflow_dockerfile_uses_same_python(self):
        content = read_text("Dockerfile.airflow")
        assert f"python{PYTHON_MAJOR_MINOR}" in content

    def test_airflow_constraints_match_airflow_python(self):
        """A URL de constraints precisa acompanhar a tag da imagem."""
        content = read_text("Dockerfile.airflow")
        image = re.search(r"FROM apache/airflow:([\d.]+)-python([\d.]+)", content)
        assert image is not None, "tag da imagem do Airflow nao reconhecida"
        airflow_version, python_version = image.group(1), image.group(2)
        expected = f"constraints-{airflow_version}/constraints-{python_version}.txt"
        assert expected in content

    def test_ci_uses_same_python(self):
        assert f'PYTHON_VERSION: "{PYTHON_MAJOR_MINOR}"' in read_text(
            ".github/workflows/ci.yml"
        )


class TestUvProjectLayout:
    def test_project_is_declared_virtual(self):
        """Sem [build-system], o uv precisa saber que nao ha pacote a instalar."""
        assert read_pyproject()["tool"]["uv"]["package"] is False
