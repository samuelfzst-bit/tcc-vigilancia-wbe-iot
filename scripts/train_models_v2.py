"""Executa seleção temporal v2 mantendo o teste de 2024 bloqueado."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from matplotlib import pyplot as plt

from src.modeling_v2 import (
    CV_YEARS,
    RANDOM_STATE,
    assert_test_locked,
    best_configs,
    evaluate_validation_2023,
    model_specs,
    rank_finalists,
    run_sensitivity,
    run_temporal_cv,
    sensitivity_candidates,
    summarize_cv,
)
from src.validation import validate_dataset


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "indisponivel"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_champion_plot(
    finalists: pd.DataFrame,
    predictions: pd.DataFrame,
    output: Path,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=False)
    for horizon, axis in zip((1, 2), axes):
        winner = finalists.loc[
            finalists["horizonte"].eq(horizon) & finalists["ranking_horizonte"].eq(1)
        ].iloc[0]
        series = predictions.loc[
            predictions["horizonte"].eq(horizon)
            & predictions["conjunto"].eq(winner["conjunto"])
            & predictions["modelo"].eq(winner["modelo"])
            & predictions["config_id"].eq(winner["config_id"])
        ].sort_values("inicio_semana_alvo")
        dates = pd.to_datetime(series["inicio_semana_alvo"])
        axis.plot(
            dates, series["observado"], label="Observado", color="#1f2937", linewidth=2
        )
        axis.plot(
            dates, series["previsto"], label="Previsto", color="#2563eb", linewidth=2
        )
        axis.set_title(
            f"t+{horizon}: {winner['modelo']} / {winner['conjunto']} "
            f"(MAE={winner['mae']:.3f})"
        )
        axis.set_ylabel("Casos semanais")
        axis.grid(alpha=0.25)
        axis.legend()
    fig.suptitle("Validação final de 2023 — teste de 2024 não aberto", fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def write_report(
    run_dir: Path,
    finalists: pd.DataFrame,
    sensitivity: pd.DataFrame,
    manifest: dict,
) -> None:
    lines = [
        "# Relatório da modelagem v2",
        "",
        f"- Dataset: `{manifest['dataset_version']}`",
        f"- SHA-256: `{manifest['dataset_sha256']}`",
        f"- Commit: `{manifest['git_commit']}`",
        "- Folds temporais: 2018, 2019, 2020, 2021 e 2022",
        "- Validação final: 2023",
        "- Teste bloqueado: 2024 (não aberto)",
        "- Métrica principal: MAE",
        "",
        "## Campeões provisórios",
        "",
        "| Horizonte | Conjunto | Modelo | Configuração | MAE 2023 | RMSE 2023 | MAE médio CV | Desvio CV |",
        "|---:|---|---|---|---:|---:|---:|---:|",
    ]
    winners = finalists.loc[finalists["ranking_horizonte"].eq(1)]
    for row in winners.itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.conjunto} | {row.modelo} | `{row.config_id}` "
            f"| {row.mae:.3f} | {row.rmse:.3f} | {row.mae_media:.3f} | {row.mae_desvio:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Sensibilidade do campeão",
            "",
            "Valores próximos entre cenários indicam que a conclusão não depende exclusivamente das janelas longas ou dos anos mais antigos.",
            "",
            "| Horizonte | Cenário | MAE médio | Desvio | Pior fold | MAE em picos |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    winner_keys = winners[["horizonte", "conjunto", "modelo", "config_id"]]
    champion_sensitivity = sensitivity.merge(
        winner_keys, on=["horizonte", "conjunto", "modelo", "config_id"]
    )
    for row in champion_sensitivity.itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.cenario_sensibilidade} | {row.mae_media:.3f} "
            f"| {row.mae_desvio:.3f} | {row.mae_pior_fold:.3f} | {row.mae_picos_media:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Regra de decisão",
            "",
            "O resultado ainda é provisório. O teste de 2024 só poderá ser aberto depois de congelar modelo, features, hiperparâmetros e critérios de alerta.",
            "",
        ]
    )
    (run_dir / "RESUMO_EXECUCAO.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/runs_v2"))
    parser.add_argument("--top-sensitivity", type=int, default=3)
    args = parser.parse_args()

    data = pd.read_parquet(args.dataset)
    validate_dataset(data)
    assert_test_locked(data)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output / stamp
    run_dir.mkdir(parents=True, exist_ok=False)

    specs = model_specs()
    fold_metrics = run_temporal_cv(data, specs=specs)
    cv_summary = summarize_cv(fold_metrics)
    selected = best_configs(cv_summary)
    validation, predictions = evaluate_validation_2023(data, selected, specs=specs)
    finalists = rank_finalists(validation, selected)
    sensitivity = run_sensitivity(
        data,
        sensitivity_candidates(finalists, top_n=args.top_sensitivity),
        specs=specs,
    )

    fold_metrics.to_csv(run_dir / "01_cv_metricas_por_fold.csv", index=False)
    cv_summary.to_csv(run_dir / "02_cv_resumo.csv", index=False)
    selected.to_csv(run_dir / "03_hiperparametros_selecionados.csv", index=False)
    validation.to_csv(run_dir / "04_metricas_validacao_2023.csv", index=False)
    finalists.to_csv(run_dir / "05_ranking_finalistas.csv", index=False)
    sensitivity.to_csv(run_dir / "06_analise_sensibilidade.csv", index=False)
    predictions.to_csv(run_dir / "07_previsoes_validacao_2023.csv", index=False)

    winners = finalists.loc[finalists["ranking_horizonte"].eq(1)][
        [
            "horizonte",
            "conjunto",
            "modelo",
            "config_id",
            "mae",
            "rmse",
            "mae_media",
            "mae_desvio",
        ]
    ].to_dict(orient="records")
    manifest = {
        "created_at_utc": stamp,
        "dataset_path": str(args.dataset),
        "dataset_sha256": sha256(args.dataset),
        "dataset_version": str(data["versao_dataset"].iloc[0]),
        "rows": len(data),
        "columns": int(data.shape[1]),
        "git_ref": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": bool(git_value("status", "--porcelain")),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "random_state": RANDOM_STATE,
        "cv_validation_years": list(CV_YEARS),
        "final_validation_year": 2023,
        "locked_test_year": 2024,
        "test_opened": False,
        "selection_metric": "mae",
        "tie_breakers": ["cv_mae_media", "rmse", "cv_mae_desvio"],
        "provisional_winners": winners,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    save_champion_plot(
        finalists, predictions, run_dir / "08_previsoes_campeoes_2023.png"
    )
    write_report(run_dir, finalists, sensitivity, manifest)
    print(f"Execução v2 salva em: {run_dir}")
    print("Teste de 2024 permanece bloqueado.")
    print(pd.DataFrame(winners).to_string(index=False))


if __name__ == "__main__":
    main()
