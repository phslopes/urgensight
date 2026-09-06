"""Testes para a logica pura de src/train.py.

Usam DataFrames/pipelines sinteticos pequenos (sem depender do dataset real)
para manter os testes rapidos e deterministicos.
"""

import json

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from src.prepare_dataset import TARGET_COLUMN, TEXT_COLUMN, VALID_TARGETS
from src.train import (
    build_pipeline,
    evaluate_pipeline,
    format_metrics_json,
    format_metrics_report,
    load_dataset,
    load_pipeline,
    main,
    save_pipeline,
    validate_columns,
)


def make_dataset(n_per_class=8):
    """Dataset sintetico com texto minimamente separavel por classe."""
    templates = {
        "normal": "routine checkup, patient stable, no acute findings, mild {i}",
        "atencao": "requires follow up, monitor condition closely, moderate {i}",
        "urgente": "emergency acute severe critical immediate action needed {i}",
    }
    rows = []
    for target, template in templates.items():
        for i in range(n_per_class):
            rows.append({TEXT_COLUMN: template.format(i=i), TARGET_COLUMN: target})
    return pd.DataFrame(rows)


class TestLoadDataset:
    def test_loads_csv_with_expected_columns(self, tmp_path):
        df = make_dataset(n_per_class=2)
        path = tmp_path / "data.csv"
        df.to_csv(path, index=False)

        loaded = load_dataset(path)

        assert list(loaded.columns) == [TEXT_COLUMN, TARGET_COLUMN]
        assert len(loaded) == len(df)

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_dataset(tmp_path / "does_not_exist.csv")


class TestValidateColumns:
    def test_passes_for_valid_dataframe(self):
        df = make_dataset(n_per_class=2)
        validate_columns(df)  # nao deve levantar excecao

    def test_raises_when_text_column_missing(self):
        df = make_dataset(n_per_class=2).drop(columns=[TEXT_COLUMN])
        with pytest.raises(ValueError):
            validate_columns(df)

    def test_raises_when_target_column_missing(self):
        df = make_dataset(n_per_class=2).drop(columns=[TARGET_COLUMN])
        with pytest.raises(ValueError):
            validate_columns(df)

    def test_raises_on_empty_dataframe(self):
        df = pd.DataFrame(columns=[TEXT_COLUMN, TARGET_COLUMN])
        with pytest.raises(ValueError):
            validate_columns(df)

    def test_raises_on_unknown_target_values(self):
        df = make_dataset(n_per_class=2)
        df.loc[0, TARGET_COLUMN] = "invalido"
        with pytest.raises(ValueError):
            validate_columns(df)


class TestBuildPipeline:
    def test_returns_sklearn_pipeline_with_tfidf_and_classifier(self):
        pipeline = build_pipeline(model_name="logreg", seed=42)
        assert isinstance(pipeline, Pipeline)
        step_names = [name for name, _ in pipeline.steps]
        assert step_names == ["tfidf", "clf"]

    def test_raises_on_unknown_model_name(self):
        with pytest.raises(ValueError):
            build_pipeline(model_name="not_a_model", seed=42)

    def test_same_seed_produces_deterministic_predictions(self):
        df = make_dataset(n_per_class=10)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]

        pipeline_a = build_pipeline(model_name="logreg", seed=42).fit(X, y)
        pipeline_b = build_pipeline(model_name="logreg", seed=42).fit(X, y)

        assert pipeline_a.predict(X).tolist() == pipeline_b.predict(X).tolist()


class TestEvaluatePipeline:
    def test_returns_accuracy_and_per_class_f1(self):
        df = make_dataset(n_per_class=10)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]
        pipeline = build_pipeline(model_name="logreg", seed=42).fit(X, y)

        metrics = evaluate_pipeline(pipeline, X, y)

        assert "accuracy" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert set(metrics["per_class"].keys()) == VALID_TARGETS
        for target in VALID_TARGETS:
            assert "f1-score" in metrics["per_class"][target]

    def test_returns_macro_f1(self):
        df = make_dataset(n_per_class=10)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]
        pipeline = build_pipeline(model_name="logreg", seed=42).fit(X, y)

        metrics = evaluate_pipeline(pipeline, X, y)

        assert "macro_f1" in metrics
        assert 0.0 <= metrics["macro_f1"] <= 1.0


class TestFormatMetricsReport:
    def test_report_contains_key_sections(self):
        df = make_dataset(n_per_class=10)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]
        pipeline = build_pipeline(model_name="logreg", seed=42).fit(X, y)
        metrics = evaluate_pipeline(pipeline, X, y)

        report = format_metrics_report(
            metrics, config={"model_name": "logreg", "seed": 42}
        )

        assert "Accuracy" in report
        assert "Macro F1" in report
        for target in VALID_TARGETS:
            assert target in report


class TestFormatMetricsJson:
    def _metrics(self):
        df = make_dataset(n_per_class=10)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]
        pipeline = build_pipeline(model_name="logreg", seed=42).fit(X, y)
        return evaluate_pipeline(pipeline, X, y)

    def test_returns_flat_scalar_mapping(self):
        """dvc metrics show espera escalares, nao estruturas aninhadas."""
        payload = format_metrics_json(
            self._metrics(), config={"model_name": "logreg", "seed": 42}
        )
        for key, value in payload.items():
            assert isinstance(value, (int, float, str)), f"{key} nao e escalar"

    def test_contains_headline_metrics(self):
        payload = format_metrics_json(
            self._metrics(), config={"model_name": "logreg", "seed": 42}
        )
        assert "accuracy" in payload
        assert "macro_f1" in payload
        assert payload["model"] == "logreg"
        assert payload["seed"] == 42

    def test_contains_per_class_f1(self):
        payload = format_metrics_json(
            self._metrics(), config={"model_name": "logreg", "seed": 42}
        )
        for target in VALID_TARGETS:
            assert f"f1_{target}" in payload

    def test_is_json_serializable(self):
        payload = format_metrics_json(
            self._metrics(), config={"model_name": "logreg", "seed": 42}
        )
        assert json.loads(json.dumps(payload)) == payload


class TestMainWritesBothMetricFiles:
    def test_writes_markdown_and_json(self, tmp_path):
        df = make_dataset(n_per_class=10)
        data_path = tmp_path / "data.csv"
        df.to_csv(data_path, index=False)

        md_out = tmp_path / "metrics.md"
        json_out = tmp_path / "metrics.json"

        main([
            "--train-path", str(data_path),
            "--test-path", str(data_path),
            "--model-out", str(tmp_path / "model.pkl"),
            "--metrics-out", str(md_out),
            "--metrics-json-out", str(json_out),
            "--max-features", "50",
        ])

        assert md_out.exists()
        payload = json.loads(json_out.read_text("utf-8"))
        assert 0.0 <= payload["accuracy"] <= 1.0


class TestSaveLoadPipeline:
    def test_roundtrip_predictions_are_identical(self, tmp_path):
        df = make_dataset(n_per_class=10)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]
        pipeline = build_pipeline(model_name="logreg", seed=42).fit(X, y)

        model_path = tmp_path / "model.pkl"
        save_pipeline(pipeline, model_path)
        loaded = load_pipeline(model_path)

        assert loaded.predict(X).tolist() == pipeline.predict(X).tolist()

    def test_save_creates_parent_directories(self, tmp_path):
        df = make_dataset(n_per_class=4)
        X, y = df[TEXT_COLUMN], df[TARGET_COLUMN]
        pipeline = build_pipeline(model_name="logreg", seed=42).fit(X, y)

        model_path = tmp_path / "nested" / "dir" / "model.pkl"
        save_pipeline(pipeline, model_path)

        assert model_path.exists()
