"""Testes para a logica pura de src/prepare_dataset.py.

Nao fazem download real (sem acesso a rede): usam DataFrames sinteticos
para validar limpeza, mapeamento de classes, split e amostragem de benchmark.
"""

import json

import pandas as pd
import pytest

from src.prepare_dataset import (
    CONDITION_TO_URGENCY,
    RAW_LABEL_COLUMN,
    RAW_TEXT_COLUMN,
    TARGET_COLUMN,
    TEXT_COLUMN,
    VALID_TARGETS,
    build_benchmark_samples,
    clean_data,
    map_labels,
    split_dataset,
)


def make_raw_df():
    return pd.DataFrame(
        {
            RAW_LABEL_COLUMN: [1, 2, 3, 4, 5, 1, None, 2, 2],
            RAW_TEXT_COLUMN: [
                "Tumor found in lung tissue after biopsy.",
                "Patient reports chronic abdominal pain.",
                "  ",
                "Acute chest pain radiating to left arm.",
                "Routine follow-up, no complications noted.",
                "Tumor found in lung tissue after biopsy.",  # duplicate
                "Missing label row should be dropped.",
                None,
                "Digestive discomfort after meals.",
            ],
        }
    )


class TestCleanData:
    def test_drops_null_label_rows(self):
        df = make_raw_df()
        cleaned = clean_data(df)
        assert cleaned[RAW_LABEL_COLUMN].isnull().sum() == 0

    def test_drops_null_and_blank_text_rows(self):
        df = make_raw_df()
        cleaned = clean_data(df)
        assert cleaned[RAW_TEXT_COLUMN].isnull().sum() == 0
        assert (cleaned[RAW_TEXT_COLUMN].str.strip() == "").sum() == 0

    def test_drops_duplicate_rows(self):
        df = make_raw_df()
        cleaned = clean_data(df)
        assert cleaned.duplicated(subset=[RAW_TEXT_COLUMN]).sum() == 0

    def test_resets_index(self):
        df = make_raw_df()
        cleaned = clean_data(df)
        assert list(cleaned.index) == list(range(len(cleaned)))

    def test_raises_on_missing_columns(self):
        df = pd.DataFrame({"foo": [1, 2]})
        with pytest.raises(ValueError):
            clean_data(df)


class TestMapLabels:
    def test_all_condition_labels_are_mapped(self):
        df = pd.DataFrame(
            {
                RAW_LABEL_COLUMN: [1, 2, 3, 4, 5],
                RAW_TEXT_COLUMN: ["a", "b", "c", "d", "e"],
            }
        )
        mapped = map_labels(df)
        assert set(mapped[TARGET_COLUMN]) <= VALID_TARGETS

    def test_output_schema_is_text_and_target(self):
        df = pd.DataFrame({RAW_LABEL_COLUMN: [1], RAW_TEXT_COLUMN: ["a"]})
        mapped = map_labels(df)
        assert list(mapped.columns) == [TEXT_COLUMN, TARGET_COLUMN]

    def test_mapping_matches_configured_dictionary(self):
        df = pd.DataFrame(
            {
                RAW_LABEL_COLUMN: list(CONDITION_TO_URGENCY.keys()),
                RAW_TEXT_COLUMN: [f"text {k}" for k in CONDITION_TO_URGENCY],
            }
        )
        mapped = map_labels(df)
        for label, expected_target in CONDITION_TO_URGENCY.items():
            row = mapped[mapped[TEXT_COLUMN] == f"text {label}"]
            assert row[TARGET_COLUMN].iloc[0] == expected_target

    def test_raises_on_unknown_label(self):
        df = pd.DataFrame({RAW_LABEL_COLUMN: [999], RAW_TEXT_COLUMN: ["a"]})
        with pytest.raises(ValueError):
            map_labels(df)


class TestSplitDataset:
    def _mapped_df(self, n_per_class=20):
        rows = []
        for target in VALID_TARGETS:
            for i in range(n_per_class):
                rows.append(
                    {TEXT_COLUMN: f"{target} sample {i}", TARGET_COLUMN: target}
                )
        return pd.DataFrame(rows)

    def test_split_respects_test_size(self):
        df = self._mapped_df()
        train_df, test_df = split_dataset(df, test_size=0.2, seed=42)
        total = len(df)
        assert abs(len(test_df) / total - 0.2) < 0.05
        assert len(train_df) + len(test_df) == total

    def test_split_is_deterministic_with_fixed_seed(self):
        df = self._mapped_df()
        train_a, test_a = split_dataset(df, test_size=0.2, seed=42)
        train_b, test_b = split_dataset(df, test_size=0.2, seed=42)
        assert train_a[TEXT_COLUMN].tolist() == train_b[TEXT_COLUMN].tolist()
        assert test_a[TEXT_COLUMN].tolist() == test_b[TEXT_COLUMN].tolist()

    def test_split_is_stratified_by_target(self):
        df = self._mapped_df(n_per_class=50)
        train_df, test_df = split_dataset(df, test_size=0.2, seed=42)
        train_props = train_df[TARGET_COLUMN].value_counts(normalize=True)
        test_props = test_df[TARGET_COLUMN].value_counts(normalize=True)
        for target in VALID_TARGETS:
            assert abs(train_props[target] - test_props[target]) < 0.05

    def test_no_overlap_between_train_and_test(self):
        df = self._mapped_df()
        train_df, test_df = split_dataset(df, test_size=0.2, seed=42)
        assert set(train_df[TEXT_COLUMN]).isdisjoint(set(test_df[TEXT_COLUMN]))


class TestBuildBenchmarkSamples:
    def _mapped_df(self, n_per_class=10):
        rows = []
        for target in VALID_TARGETS:
            for i in range(n_per_class):
                rows.append(
                    {TEXT_COLUMN: f"{target} sample {i}", TARGET_COLUMN: target}
                )
        return pd.DataFrame(rows)

    def test_samples_n_per_class(self):
        df = self._mapped_df()
        samples = build_benchmark_samples(df, n_per_class=3, seed=42)
        counts = pd.Series([s[TARGET_COLUMN] for s in samples]).value_counts()
        for target in VALID_TARGETS:
            assert counts[target] == 3

    def test_samples_are_json_serializable(self, tmp_path):
        df = self._mapped_df()
        samples = build_benchmark_samples(df, n_per_class=2, seed=42)
        out_path = tmp_path / "benchmark_samples.json"
        out_path.write_text(
            json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert loaded == samples

    def test_each_sample_has_text_and_target_keys(self):
        df = self._mapped_df()
        samples = build_benchmark_samples(df, n_per_class=2, seed=42)
        for sample in samples:
            assert set(sample.keys()) == {TEXT_COLUMN, TARGET_COLUMN}

    def test_deterministic_with_fixed_seed(self):
        df = self._mapped_df()
        samples_a = build_benchmark_samples(df, n_per_class=3, seed=42)
        samples_b = build_benchmark_samples(df, n_per_class=3, seed=42)
        assert samples_a == samples_b
