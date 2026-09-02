"""Valida o fixture de dummy training usado pelo CI (Etapa 3).

O job smoke-train do GitHub Actions treina um modelo em miniatura sobre este
arquivo. Se ele perder colunas ou classes, o CI quebra de forma obscura --
este teste faz a falha aparecer localmente e com mensagem clara.
"""

from pathlib import Path

import pandas as pd

from src.prepare_dataset import TARGET_COLUMN, TEXT_COLUMN, VALID_TARGETS

FIXTURE_PATH = Path("tests/fixtures/sample_dataset.csv")


def test_fixture_exists():
    assert FIXTURE_PATH.exists(), f"{FIXTURE_PATH} ausente -- ver Task 3 do plano."


def test_fixture_has_required_columns():
    df = pd.read_csv(FIXTURE_PATH)
    assert {TEXT_COLUMN, TARGET_COLUMN} <= set(df.columns)


def test_fixture_covers_all_urgency_classes():
    df = pd.read_csv(FIXTURE_PATH)
    assert set(df[TARGET_COLUMN]) == VALID_TARGETS


def test_fixture_has_no_empty_texts():
    df = pd.read_csv(FIXTURE_PATH)
    assert df[TEXT_COLUMN].str.strip().ne("").all()
