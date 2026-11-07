"""Gera diagnosticos pos-hoc sem reabrir ou retreinar o holdout de 2024."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.posthoc_analysis import (
    dashboard_predictions,
    monthly_error_summary,
    poisson_coefficients,
    threshold_sensitivity,
    validate_final_run,
    weekly_error_audit,
)


def save_error_plot(audit: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    for horizon, axis in zip((1, 2), axes):
        frame = audit.loc[audit["horizonte"].eq(horizon)].sort_values(
            "inicio_semana_alvo"
        )
        colors = frame["erro"].map(
            lambda value: "#dc2626" if value > 0 else "#2563eb"
        )
        axis.bar(frame["inicio_semana_alvo"], frame["erro"], color=colors, width=5)
        axis.axhline(0, color="#111827", linewidth=0.8)
        axis.set_title(f"Erro semanal pos-hoc — t+{horizon}")
        axis.set_ylabel("Previsto - observado")
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Auditoria pos-hoc dos erros de 2024", fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_coefficient_plot(coefficients: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for horizon, axis in zip((1, 2), axes):
        frame = (
            coefficients.loc[coefficients["horizonte"].eq(horizon)]
            .nsmallest(12, "ranking_modulo")
            .sort_values("coeficiente_log_padronizado")
        )
        colors = frame["coeficiente_log_padronizado"].map(
            lambda value: "#dc2626" if value > 0 else "#2563eb"
        )
        axis.barh(
            frame["feature_transformada"],
            frame["coeficiente_log_padronizado"],
            color=colors,
        )
        axis.axvline(0, color="#111827", linewidth=0.8)
        axis.set_title(f"12 maiores coeficientes — t+{horizon}")
        axis.set_xlabel("Coeficiente padronizado na escala log")
        axis.grid(axis="x", alpha=0.25)
    fig.suptitle("Interpretacao do Poisson congelado — nao causal", fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_threshold_plot(sensitivity: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for horizon, axis in zip((1, 2), axes):
        frame = sensitivity.loc[sensitivity["horizonte"].eq(horizon)]
        axis.plot(frame["limiar_alerta"], frame["f1_alerta"], marker="o", label="F1")
        axis.plot(
            frame["limiar_alerta"],
            frame["acuracia_balanceada"],
            marker="o",
            label="Acuracia balanceada",
        )
        axis.axvline(4, linestyle="--", color="#dc2626", label="Oficial: 4")
        axis.set_title(f"t+{horizon}")
        axis.set_xlabel("Limiar semanal")
        axis.set_xticks(sorted(frame["limiar_alerta"].unique()))
        axis.grid(alpha=0.25)
        axis.legend()
    axes[0].set_ylabel("Metrica")
    fig.suptitle("Sensibilidade pos-hoc dos limiares", fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def build_report(
    metrics: pd.DataFrame,
    sensitivity: pd.DataFrame,
    audit: pd.DataFrame,
    coefficients: pd.DataFrame,
    manifest: dict,
) -> str:
    champion = metrics.loc[metrics["modelo_congelado"].astype(bool)].sort_values(
        "horizonte"
    )
    lines = [
        "# Analise pos-hoc do teste final de 2024",
        "",
        "> Esta analise nao altera modelo, features, hiperparametros, limiar oficial ou resultados confirmatorios.",
        "",
        f"- Commit da avaliacao: `{manifest['git_commit']}`",
        f"- Dataset: `{manifest['dataset_sha256']}`",
        "- Limiar oficial congelado: **4 casos semanais**",
        "- Faixa exploratoria para o dashboard: **atencao entre 2 e menos de 4 casos**",
        "",
        "## Desempenho confirmado",
        "",
        "| Horizonte | MAE | RMSE | Bias | Razao de calibracao |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in champion.itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.mae:.3f} | {row.rmse:.3f} "
            f"| {row.bias:.3f} | {row.razao_calibracao:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Sensibilidade descritiva dos limiares",
            "",
            "| Horizonte | Limiar | Alertas observados | F1 | Especificidade | Status |",
            "|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in sensitivity.itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.limiar_alerta:g} "
            f"| {row.alertas_observados}/{row.semanas} | {row.f1_alerta:.3f} "
            f"| {row.especificidade:.3f} | {row.status_metodologico} |"
        )

    lines.extend(["", "## Maiores erros semanais", ""])
    for horizon in (1, 2):
        lines.extend(
            [
                f"### t+{horizon}",
                "",
                "| Semana | Observado | Previsto | Erro | Tipo de alerta |",
                "|---|---:|---:|---:|---|",
            ]
        )
        top = audit.loc[audit["horizonte"].eq(horizon)].nsmallest(
            5, "ranking_erro_absoluto"
        )
        for row in top.itertuples(index=False):
            lines.append(
                f"| {row.inicio_semana_alvo.date()} | {row.observado:.0f} "
                f"| {row.previsto:.2f} | {row.erro:+.2f} | {row.tipo_alerta} |"
            )
        lines.append("")

    lines.extend(["## Coeficientes de maior magnitude", ""])
    for horizon in (1, 2):
        lines.extend(
            [
                f"### t+{horizon}",
                "",
                "| Feature transformada | Coeficiente | Variacao por 1 DP |",
                "|---|---:|---:|",
            ]
        )
        top = coefficients.loc[coefficients["horizonte"].eq(horizon)].nsmallest(
            10, "ranking_modulo"
        )
        for row in top.itertuples(index=False):
            lines.append(
                f"| `{row.feature_transformada}` | {row.coeficiente_log_padronizado:+.4f} "
                f"| {row.variacao_percentual_por_1dp:+.1f}% |"
            )
        lines.append("")

    lines.extend(
        [
            "## Limites de interpretacao",
            "",
            "- Coeficientes descrevem associacoes condicionais do modelo, nao causalidade.",
            "- Features climaticas correlacionadas dividem efeito; coeficientes isolados nao devem ser tratados como importancia causal.",
            "- A faixa de atencao em 2 casos e uma camada operacional exploratoria. O alerta confirmado continua em 4.",
            "- Sensor IoT e previsao epidemiologica permanecem modulos distintos; esta analise nao valida diagnostico por pH, turbidez ou TDS.",
            "",
        ]
    )
    return "\n".join(lines)


def run(run_dir: Path, output_dir: Path) -> None:
    manifest = validate_final_run(run_dir)
    protocol = json.loads(
        (run_dir / "00_protocolo_congelado.json").read_text(encoding="utf-8")
    )
    metrics = pd.read_csv(run_dir / "01_metricas_teste_2024.csv")
    predictions = pd.read_csv(run_dir / "03_previsoes_teste_2024.csv")

    sensitivity = threshold_sensitivity(predictions)
    audit = weekly_error_audit(predictions)
    monthly = monthly_error_summary(audit)
    coefficients = pd.concat(
        [
            poisson_coefficients(run_dir / "05_modelo_poisson_t1.joblib", 1),
            poisson_coefficients(run_dir / "05_modelo_poisson_t2.joblib", 2),
        ],
        ignore_index=True,
    )
    dashboard = dashboard_predictions(
        predictions, protocol, manifest, execution_id=run_dir.name
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    sensitivity.to_csv(output_dir / "01_sensibilidade_limiares.csv", index=False)
    audit.to_csv(output_dir / "02_auditoria_erros_semanais.csv", index=False)
    monthly.to_csv(output_dir / "03_resumo_erros_mensais.csv", index=False)
    coefficients.to_csv(output_dir / "04_coeficientes_poisson.csv", index=False)
    dashboard.to_csv(output_dir / "05_previsoes_dashboard_2024.csv", index=False)
    save_error_plot(audit, output_dir / "06_erros_semanais_2024.png")
    save_coefficient_plot(coefficients, output_dir / "07_coeficientes_poisson.png")
    save_threshold_plot(sensitivity, output_dir / "08_sensibilidade_limiares.png")
    report = build_report(metrics, sensitivity, audit, coefficients, manifest)
    (output_dir / "RELATORIO_POS_HOC_2024.md").write_text(report, encoding="utf-8")
    print(f"Analise pos-hoc concluida: {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.run_dir, args.output_dir)
