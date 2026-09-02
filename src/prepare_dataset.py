"""Preparacao do dataset de triagem de laudos medicos.

Baixa o Medical Abstracts TC Corpus (dominio publico, ver docs/dataset.md),
limpa os dados, mapeia as 5 classes clinicas originais para as 3 classes de
urgencia do projeto (normal, atencao, urgente), faz o split treino/teste com
seed fixa e gera as amostras de benchmark em data/benchmark_samples.json.

Uso:
    python -m src.prepare_dataset --seed 42 --test-size 0.2
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import requests
from sklearn.model_selection import train_test_split

RAW_TRAIN_URL = (
    "https://raw.githubusercontent.com/sebischair/Medical-Abstracts-TC-Corpus"
    "/main/medical_tc_train.csv"
)
RAW_TEST_URL = (
    "https://raw.githubusercontent.com/sebischair/Medical-Abstracts-TC-Corpus"
    "/main/medical_tc_test.csv"
)

RAW_LABEL_COLUMN = "condition_label"
RAW_TEXT_COLUMN = "medical_abstract"
REQUIRED_RAW_COLUMNS = {RAW_LABEL_COLUMN, RAW_TEXT_COLUMN}

TEXT_COLUMN = "text"
TARGET_COLUMN = "target"

# As classes originais do corpus descrevem categorias clinicas (nao
# urgencia). Mapeamos para as 3 classes do projeto por criterio de
# severidade/necessidade de resposta clinica -- ver docs/dataset.md.
CONDITION_LABEL_NAMES = {
    1: "neoplasms",
    2: "digestive_system_diseases",
    3: "nervous_system_diseases",
    4: "cardiovascular_diseases",
    5: "general_pathological_conditions",
}
CONDITION_TO_URGENCY = {
    4: "urgente",  # doencas cardiovasculares: risco agudo/potencialmente fatal
    1: "atencao",  # neoplasias: requer investigacao/acompanhamento especializado
    3: "atencao",  # doencas do sistema nervoso: requer avaliacao especializada
    2: "normal",  # doencas digestivas: predominantemente rotina
    5: "normal",  # condicoes patologicas gerais: predominantemente rotina
}
VALID_TARGETS = {"normal", "atencao", "urgente"}


def download_raw_data(dest_dir: Path, force: bool = False) -> tuple[Path, Path]:
    """Baixa os CSVs de treino/teste originais do corpus para dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    train_path = dest_dir / "medical_tc_train.csv"
    test_path = dest_dir / "medical_tc_test.csv"

    for url, path in ((RAW_TRAIN_URL, train_path), (RAW_TEST_URL, test_path)):
        if path.exists() and not force:
            continue
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)

    return train_path, test_path


def load_raw_data(train_path: Path, test_path: Path) -> pd.DataFrame:
    """Carrega e concatena os CSVs brutos de treino/teste em um unico DataFrame."""
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    return pd.concat([train_df, test_df], ignore_index=True)


def compute_cleaning_stats(df: pd.DataFrame) -> dict:
    """Calcula estatisticas de qualidade (nulos, vazios, duplicados) antes da limpeza."""
    _validate_raw_columns(df)
    text = df[RAW_TEXT_COLUMN].astype("string")
    return {
        "total_rows": int(len(df)),
        "null_label_rows": int(df[RAW_LABEL_COLUMN].isnull().sum()),
        "null_or_blank_text_rows": int(
            (text.isnull() | (text.str.strip() == "")).sum()
        ),
        "duplicate_text_rows": int(df.duplicated(subset=[RAW_TEXT_COLUMN]).sum()),
    }


def _validate_raw_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_RAW_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Colunas obrigatorias ausentes no dataset bruto: {sorted(missing)}"
        )


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove registros nulos, com texto vazio/em branco e duplicados."""
    _validate_raw_columns(df)

    cleaned = df.copy()
    cleaned[RAW_TEXT_COLUMN] = cleaned[RAW_TEXT_COLUMN].astype("string")

    cleaned = cleaned.dropna(subset=[RAW_LABEL_COLUMN, RAW_TEXT_COLUMN])
    cleaned = cleaned[cleaned[RAW_TEXT_COLUMN].str.strip() != ""]
    cleaned[RAW_TEXT_COLUMN] = cleaned[RAW_TEXT_COLUMN].str.strip()
    cleaned = cleaned.drop_duplicates(subset=[RAW_TEXT_COLUMN])

    return cleaned.reset_index(drop=True)


def map_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia condition_label (1-5) para a coluna target (normal/atencao/urgente)."""
    _validate_raw_columns(df)

    unknown_labels = set(df[RAW_LABEL_COLUMN].unique()) - set(CONDITION_TO_URGENCY)
    if unknown_labels:
        raise ValueError(f"Rotulos desconhecidos encontrados: {sorted(unknown_labels)}")

    mapped = pd.DataFrame(
        {
            TEXT_COLUMN: df[RAW_TEXT_COLUMN].values,
            TARGET_COLUMN: df[RAW_LABEL_COLUMN].map(CONDITION_TO_URGENCY).values,
        }
    )
    return mapped


def compute_class_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna contagem e proporcao de amostras por classe de urgencia."""
    counts = df[TARGET_COLUMN].value_counts()
    proportions = df[TARGET_COLUMN].value_counts(normalize=True)
    return pd.DataFrame({"count": counts, "proportion": proportions}).sort_values(
        "count", ascending=False
    )


def split_dataset(
    df: pd.DataFrame, test_size: float = 0.2, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split treino/teste estratificado por classe, com seed fixa."""
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=seed,
        stratify=df[TARGET_COLUMN],
    )
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def build_benchmark_samples(
    df: pd.DataFrame, n_per_class: int = 15, seed: int = 42
) -> list:
    """Amostra n_per_class registros por classe para benchmark/teste manual."""
    samples = []
    for target in sorted(VALID_TARGETS):
        subset = df[df[TARGET_COLUMN] == target]
        n = min(n_per_class, len(subset))
        sampled = subset.sample(n=n, random_state=seed)
        samples.extend(sampled[[TEXT_COLUMN, TARGET_COLUMN]].to_dict(orient="records"))
    return samples


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--benchmark-per-class", type=int, default=15)
    parser.add_argument("--force-download", action="store_true")

    # Flags de estagio: o pipeline DVC separa o download (dependente de rede)
    # do processamento (deterministico), para que mudar um parametro de split
    # nao rebaixe os 17 MB de data/raw. Ver dvc.yaml.
    stage_group = parser.add_mutually_exclusive_group()
    stage_group.add_argument("--download-only", action="store_true")
    stage_group.add_argument("--skip-download", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    raw_dir = args.data_dir / "raw"
    processed_dir = args.data_dir / "processed"

    if args.skip_download:
        train_path = raw_dir / "medical_tc_train.csv"
        test_path = raw_dir / "medical_tc_test.csv"
        for path in (train_path, test_path):
            if not path.exists():
                raise FileNotFoundError(
                    f"Arquivo bruto ausente: {path}. "
                    "Rode o estagio de download antes (--download-only)."
                )
    else:
        print(f"Baixando dataset bruto em {raw_dir} ...")
        train_path, test_path = download_raw_data(raw_dir, force=args.force_download)

    if args.download_only:
        print("Download concluido (--download-only): nada mais a fazer.")
        return

    processed_dir.mkdir(parents=True, exist_ok=True)

    raw_df = load_raw_data(train_path, test_path)
    stats = compute_cleaning_stats(raw_df)
    print(f"Amostras brutas: {stats['total_rows']}")
    print(
        "Removendo: "
        f"{stats['null_label_rows']} rotulo(s) nulo(s), "
        f"{stats['null_or_blank_text_rows']} texto(s) vazio(s)/nulo(s), "
        f"{stats['duplicate_text_rows']} duplicata(s)"
    )

    cleaned_df = clean_data(raw_df)
    mapped_df = map_labels(cleaned_df)
    print(f"Amostras apos limpeza e mapeamento: {len(mapped_df)}")

    distribution = compute_class_distribution(mapped_df)
    print("Distribuicao de classes:")
    print(distribution)

    train_df, test_df = split_dataset(
        mapped_df, test_size=args.test_size, seed=args.seed
    )
    train_df.to_csv(processed_dir / "train.csv", index=False)
    test_df.to_csv(processed_dir / "test.csv", index=False)
    print(f"Treino: {len(train_df)} amostras | Teste: {len(test_df)} amostras")

    benchmark_samples = build_benchmark_samples(
        mapped_df, n_per_class=args.benchmark_per_class, seed=args.seed
    )
    benchmark_path = args.data_dir / "benchmark_samples.json"
    benchmark_path.write_text(
        json.dumps(benchmark_samples, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Amostras de benchmark salvas em {benchmark_path} ({len(benchmark_samples)} amostras)"
    )

    _write_dataset_report(stats, mapped_df, distribution, train_df, test_df)


def _write_dataset_report(
    stats: dict,
    mapped_df: pd.DataFrame,
    distribution: pd.DataFrame,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> None:
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_path = docs_dir / "dataset_distribution.md"

    lines = [
        "# Distribuicao do Dataset (gerado automaticamente)",
        "",
        "## Limpeza",
        f"- Amostras brutas: {stats['total_rows']}",
        f"- Rotulos nulos removidos: {stats['null_label_rows']}",
        f"- Textos nulos/vazios removidos: {stats['null_or_blank_text_rows']}",
        f"- Duplicatas removidas: {stats['duplicate_text_rows']}",
        f"- Amostras finais (apos limpeza): {len(mapped_df)}",
        "",
        "## Distribuicao de classes (dataset completo)",
        "",
        "| Classe | Contagem | Proporcao |",
        "|---|---|---|",
    ]
    for target, row in distribution.iterrows():
        lines.append(f"| {target} | {int(row['count'])} | {row['proportion']:.1%} |")

    lines += [
        "",
        "## Split treino/teste",
        f"- Treino: {len(train_df)} amostras",
        f"- Teste: {len(test_df)} amostras",
    ]

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Relatorio de distribuicao salvo em {report_path}")


if __name__ == "__main__":
    main()
