"""Executa o challenger XGBoost mantendo o teste de 2024 bloqueado."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost
from matplotlib import pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.modeling_v2 import CV_YEARS, RANDOM_STATE, assert_test_locked
from src.validation import validate_dataset
from src.xgboost_challenger import (
    MAX_CV_SD_RATIO,
    MAX_PEAK_MAE_RATIO,
    MIN_MAE_IMPROVEMENT,
    decide_challenger,
    evaluate_challenger_2023,
    run_challenger_cv,
    select_xgboost_configs,
    summarize_challenger_cv,
    xgboost_specs,
)


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


def save_plot(predictions: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=False)
    colors = {"poisson": "#2563eb", "xgboost_poisson": "#dc2626"}
    for horizon, axis in zip((1, 2), axes):
        series = predictions.loc[predictions["horizonte"].eq(horizon)].copy()
        observed = series.loc[series["modelo"].eq("poisson")].sort_values(
            "inicio_semana_alvo"
        )
        dates = pd.to_datetime(observed["inicio_semana_alvo"])
        axis.plot(dates, observed["observado"], label="Observado", color="#111827")
        for model_name in ("poisson", "xgboost_poisson"):
            model_series = series.loc[series["modelo"].eq(model_name)].sort_values(
                "inicio_semana_alvo"
            )
            label = "Poisson" if model_name == "poisson" else "XGBoost Poisson"
            axis.plot(
                dates,
                model_series["previsto"],
                label=label,
                color=colors[model_name],
                linewidth=2,
            )
        axis.set_title(f"Validação 2023 — t+{horizon}")
        axis.set_ylabel("Casos semanais")
        axis.grid(alpha=0.25)
        axis.legend()
    fig.suptitle("Challenger XGBoost — teste de 2024 não aberto", fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def write_report(
    run_dir: Path,
    selected: pd.DataFrame,
    validation: pd.DataFrame,
    decision: pd.DataFrame,
    manifest: dict,
) -> None:
    lines = [
        "# Challenger XGBoost",
        "",
        f"- Dataset: `{manifest['dataset_version']}`",
        f"- SHA-256: `{manifest['dataset_sha256']}`",
        f"- Commit: `{manifest['git_commit']}`",
        "- Features: clima + sazonalidade, idênticas às do Poisson",
        "- Folds temporais: 2018–2022",
        "- Validação final: 2023",
        "- Teste de 2024: bloqueado e não aberto",
        "",
        "## Regra pré-registrada",
        "",
        (
            f"O XGBoost só substitui o Poisson se melhorar o MAE de 2023 em "
            f"pelo menos {MIN_MAE_IMPROVEMENT:.0%}, não piorar o MAE médio do "
            f"CV, mantiver desvio do CV em até {MAX_CV_SD_RATIO:.2f}x e MAE "
            f"de picos em até {MAX_PEAK_MAE_RATIO:.2f}x."
        ),
        "",
        "## Configurações selecionadas apenas pelo CV",
        "",
        "| Horizonte | Configuração | MAE médio CV | Desvio CV | MAE picos CV |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in selected.itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | `{row.config_id}` | {row.mae_media:.3f} "
            f"| {row.mae_desvio:.3f} | {row.mae_picos_media:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Validação final de 2023",
            "",
            "| Horizonte | Modelo | MAE | RMSE | Viés | MAE picos |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in validation.sort_values(["horizonte", "modelo"]).itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.modelo} | {row.mae:.3f} | {row.rmse:.3f} "
            f"| {row.bias:.3f} | {row.mae_picos:.3f} |"
        )
    lines.extend(["", "## Decisão", ""])
    for row in decision.itertuples(index=False):
        verdict = "substitui" if row.xgboost_substitui_poisson else "não substitui"
        lines.append(
            f"- **t+{row.horizonte}:** XGBoost {verdict} o Poisson. "
            f"Melhora relativa de MAE: {row.melhora_relativa_mae:.1%}. "
            f"Modelo recomendado: `{row.modelo_recomendado}`."
        )
    lines.extend(
        [
            "",
            "A decisão é definitiva para este protocolo. O teste de 2024 não pode ser usado para trocar o modelo.",
            "",
        ]
    )
    (run_dir / "RESUMO_EXECUCAO.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/xgboost_challenger")
    )
    args = parser.parse_args()

    data = pd.read_parquet(args.dataset)
    validate_dataset(data)
    assert_test_locked(data)
    specs = xgboost_specs()

    fold_metrics = run_challenger_cv(data, specs=specs)
    cv_summary = summarize_challenger_cv(fold_metrics)
    selected = select_xgboost_configs(cv_summary)
    validation, predictions = evaluate_challenger_2023(data, selected, specs=specs)
    decision = decide_challenger(validation, cv_summary)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    fold_metrics.to_csv(run_dir / "01_cv_metricas_por_fold.csv", index=False)
    cv_summary.to_csv(run_dir / "02_cv_resumo.csv", index=False)
    selected.to_csv(run_dir / "03_xgboost_config_selecionada.csv", index=False)
    validation.to_csv(run_dir / "04_validacao_2023.csv", index=False)
    decision.to_csv(run_dir / "05_decisao_challenger.csv", index=False)
    predictions.to_csv(run_dir / "06_previsoes_2023.csv", index=False)
    save_plot(predictions, run_dir / "07_poisson_vs_xgboost_2023.png")

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
        "xgboost": xgboost.__version__,
        "random_state": RANDOM_STATE,
        "cv_validation_years": list(CV_YEARS),
        "final_validation_year": 2023,
        "locked_test_year": 2024,
        "test_opened": False,
        "feature_set": "clima",
        "poisson_config": "alpha=1",
        "decision_rule": {
            "minimum_relative_mae_improvement": MIN_MAE_IMPROVEMENT,
            "maximum_cv_sd_ratio": MAX_CV_SD_RATIO,
            "maximum_peak_mae_ratio": MAX_PEAK_MAE_RATIO,
            "cv_mean_must_not_worsen": True,
        },
        "decision": decision.to_dict(orient="records"),
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_report(run_dir, selected, validation, decision, manifest)
    print(f"Execução do challenger salva em: {run_dir}")
    print("Teste de 2024 permanece bloqueado.")
    print(decision.to_string(index=False))


if __name__ == "__main__":
    main()
