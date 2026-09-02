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


# Versoes ditadas pelas constraints oficiais do Airflow 2.9.3
# (constraints-3.12.txt). O modelo e treinado sob elas dentro do container
# do Airflow; a API precisa desserializar sob exatamente as mesmas.
AIRFLOW_PINNED = {"numpy": "1.26.4", "pandas": "2.1.4"}


class TestDependencyGroups:
    def test_declares_dependency_groups(self):
        assert "dependency-groups" in read_pyproject()

    def test_has_no_legacy_optional_dependencies(self):
        """Grupos PEP 735 substituem os extras; manter ambos duplica a verdade."""
        assert "optional-dependencies" not in read_pyproject()["project"]

    def test_dev_group_includes_pipeline_group(self):
        dev = read_pyproject()["dependency-groups"]["dev"]
        assert {"include-group": "pipeline"} in dev

    def test_numpy_is_pinned_to_airflow_version(self):
        deps = read_pyproject()["project"]["dependencies"]
        assert f"numpy=={AIRFLOW_PINNED['numpy']}" in deps

    def test_pandas_is_pinned_to_airflow_version_in_pipeline_group(self):
        pipeline = read_pyproject()["dependency-groups"]["pipeline"]
        assert f"pandas=={AIRFLOW_PINNED['pandas']}" in pipeline

    def test_api_runtime_excludes_pipeline_only_packages(self):
        """src/app.py nao importa pandas nem requests: eles nao vao para a imagem."""
        deps = " ".join(read_pyproject()["project"]["dependencies"])
        assert "pandas" not in deps
        assert "requests" not in deps

    def test_dvc_is_not_a_runtime_dependency(self):
        deps = " ".join(read_pyproject()["project"]["dependencies"])
        assert "dvc" not in deps


class TestLockfileMatchesPins:
    def test_lock_resolves_pinned_versions(self):
        """O lock e a fonte de verdade real; os pins precisam ter chegado nele."""
        lock = read_text("uv.lock")
        for package, version in AIRFLOW_PINNED.items():
            assert f'name = "{package}"\nversion = "{version}"' in lock
