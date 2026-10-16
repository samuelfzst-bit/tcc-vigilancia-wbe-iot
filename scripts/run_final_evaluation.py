"""Congela o protocolo e abre o teste de 2024 uma única vez."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from matplotlib import pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.final_evaluation import (
    CONFIRMATION_TOKEN,
    EXPECTED_DATASET_SHA256,
    build_frozen_protocol,
    evaluate_locked_2024,
    validate_frozen_protocol,
)
from src.modeling_v2 import assert_test_locked
from src.validation import validate_dataset


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "indisponivel"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_final_plot(predictions: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=False)
    for horizon, axis in zip((1, 2), axes):
        series = predictions.loc[predictions["horizonte"].eq(horizon)].sort_values(
            "inicio_semana_alvo"
        )
        dates = pd.to_datetime(series["inicio_semana_alvo"])
        axis.plot(dates, series["observado"], color="#111827", label="Observado")
        axis.plot(
            dates,
            series["previsto"],
            color="#2563eb",
            linewidth=2,
            label="Poisson congelado",
        )
        threshold = float(series["limiar_alerta"].iloc[0])
        axis.axhline(
            threshold,
            color="#dc2626",
            linestyle="--",
            alpha=0.8,
            label=f"Limiar de alerta ({threshold:g})",
        )
        axis.set_title(f"Teste final de 2024 — t+{horizon}")
        axis.set_ylabel("Casos semanais")
        axis.grid(alpha=0.25)
        axis.legend()
    fig.suptitle("Avaliação final — modelo congelado antes do holdout", fontsize=14)
    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)


def pretest_note(protocol: dict) -> str:
    lines = [
        "# Protocolo congelado antes do teste final",
        "",
        f"- Versão: `{protocol['versao_protocolo']}`",
        f"- Dataset: `{protocol['dataset']['versao']}`",
        f"- SHA-256 do dataset: `{protocol['dataset']['sha256']}`",
        f"- SHA-256 do protocolo: `{protocol['sha256_protocolo']}`",
        "- Campeão t+1: Poisson `alpha=1`",
        "- Campeão t+2: Poisson `alpha=1`",
        "- Features: clima + sazonalidade",
        "- Treino final: 2010–2023",
        "- Teste único: 2024",
        "",
        "## Limiares estatísticos de alerta",
        "",
        "| Horizonte | Limiar | Q75 antes do arredondamento |",
        "|---:|---:|---:|",
    ]
    for champion in protocol["campeoes"]:
        lines.append(
            f"| t+{champion['horizonte']} | {champion['limiar_alerta']} "
            f"| {champion['quantil_75_desenvolvimento']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Este limiar identifica semanas de incidência historicamente elevada no protótipo. Não é um limiar clínico oficial.",
            "",
            "Depois da abertura, nenhum resultado de 2024 pode alterar o protocolo.",
            "",
        ]
    )
    return "\n".join(lines)


def final_report(
    protocol: dict, metrics: pd.DataFrame, alerts: pd.DataFrame, receipt: dict
) -> str:
    final_metrics = metrics.loc[metrics["modelo_congelado"]].sort_values("horizonte")
    lines = [
        "# Resultado do teste final de 2024",
        "",
        f"- Protocolo: `{protocol['versao_protocolo']}`",
        f"- SHA-256 do protocolo: `{protocol['sha256_protocolo']}`",
        f"- Abertura registrada em UTC: `{receipt['aberto_em_utc']}`",
        "- Modelo mantido independentemente do resultado: Poisson `alpha=1`",
        "",
        "## Métricas do campeão congelado",
        "",
        "| Horizonte | n | MAE | IC95% MAE | RMSE | Viés | MAE picos | Razão de calibração |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in final_metrics.itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.n} | {row.mae:.3f} "
            f"| [{row.mae_ic95_inferior:.3f}; {row.mae_ic95_superior:.3f}] "
            f"| {row.rmse:.3f} | {row.bias:.3f} | {row.mae_picos:.3f} "
            f"| {row.razao_calibracao:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Desempenho do alerta estatístico",
            "",
            "| Horizonte | Limiar | Precisão | Recall | F1 | Acurácia balanceada | FP | FN |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in alerts.sort_values("horizonte").itertuples(index=False):
        lines.append(
            f"| t+{row.horizonte} | {row.limiar_alerta:g} "
            f"| {row.precisao_alerta:.3f} | {row.recall_alerta:.3f} "
            f"| {row.f1_alerta:.3f} | {row.acuracia_balanceada:.3f} "
            f"| {row.falsos_positivos} | {row.falsos_negativos} |"
        )
    lines.extend(
        [
            "",
            "Os baselines no arquivo de métricas servem apenas para contextualização. Eles não podem substituir o campeão após a abertura de 2024.",
            "",
        ]
    )
    return "\n".join(lines)


def freeze(dataset_path: Path, output_root: Path) -> Path:
    dataset_hash = file_sha256(dataset_path)
    if dataset_hash != EXPECTED_DATASET_SHA256:
        raise RuntimeError("Dataset diferente do snapshot oficial; congelamento recusado")
    data = pd.read_parquet(dataset_path)
    validate_dataset(data)
    assert_test_locked(data)
    stamp = utc_stamp()
    run_dir = output_root / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    protocol = build_frozen_protocol(
        data,
        dataset_hash,
        created_at_utc=stamp,
        git_commit=git_value("rev-parse", "HEAD"),
    )
    write_json(run_dir / "00_protocolo_congelado.json", protocol)
    (run_dir / "00_LEIA_ANTES.md").write_text(pretest_note(protocol), encoding="utf-8")
    print(f"RUN_DIR={run_dir}")
    print("Protocolo congelado. O teste de 2024 ainda não foi avaliado.")
    return run_dir


def evaluate(dataset_path: Path, run_dir: Path, confirmation: str) -> None:
    if confirmation != CONFIRMATION_TOKEN:
        raise RuntimeError(
            "Confirmação inválida. O teste final não foi aberto. "
            f"Use exatamente: {CONFIRMATION_TOKEN}"
        )
    protocol_path = run_dir / "00_protocolo_congelado.json"
    if not protocol_path.exists():
        raise FileNotFoundError("Manifesto pré-teste não encontrado")
    protocol = read_json(protocol_path)
    validate_frozen_protocol(protocol)
    dataset_hash = file_sha256(dataset_path)
    if dataset_hash != protocol["dataset"]["sha256"]:
        raise RuntimeError("Dataset divergiu depois do congelamento")

    lock_path = run_dir.parent / f"TESTE_2024_ABERTO_{dataset_hash[:16]}.json"
    now = utc_stamp()
    if lock_path.exists():
        lock = read_json(lock_path)
        if Path(lock["run_dir"]).resolve() != run_dir.resolve():
            raise RuntimeError("O holdout deste dataset já foi aberto em outra execução")
        if lock.get("status") == "concluido":
            raise RuntimeError("O teste final de 2024 já foi concluído; reexecução recusada")
    else:
        lock = {
            "status": "abrindo",
            "aberto_em_utc": now,
            "run_dir": str(run_dir.resolve()),
            "dataset_sha256": dataset_hash,
            "protocolo_sha256": protocol["sha256_protocolo"],
        }
        write_json(lock_path, lock)

    data = pd.read_parquet(dataset_path)
    validate_dataset(data)
    assert_test_locked(data)
    metrics, alerts, predictions, fitted_models = evaluate_locked_2024(data, protocol)

    metrics.to_csv(run_dir / "01_metricas_teste_2024.csv", index=False)
    alerts.to_csv(run_dir / "02_metricas_alerta_2024.csv", index=False)
    predictions.to_csv(run_dir / "03_previsoes_teste_2024.csv", index=False)
    save_final_plot(predictions, run_dir / "04_observado_vs_previsto_2024.png")
    for horizon, model in fitted_models.items():
        joblib.dump(model, run_dir / f"05_modelo_poisson_t{horizon}.joblib")

    receipt = {
        **lock,
        "status": "concluido",
        "concluido_em_utc": utc_stamp(),
        "modelos_avaliados": ["poisson_final"],
        "horizontes": [1, 2],
        "reabertura_permitida": False,
    }
    write_json(run_dir / "06_RECIBO_ABERTURA_2024.json", receipt)
    (run_dir / "RESUMO_EXECUCAO.md").write_text(
        final_report(protocol, metrics, alerts, receipt), encoding="utf-8"
    )
    result_files = sorted(path for path in run_dir.iterdir() if path.is_file())
    manifest = {
        "created_at_utc": receipt["concluido_em_utc"],
        "dataset_sha256": dataset_hash,
        "protocol_sha256": protocol["sha256_protocolo"],
        "git_ref": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": bool(git_value("status", "--porcelain")),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "test_year": 2024,
        "test_opened_once": True,
        "model_change_after_test_allowed": False,
        "files": {path.name: file_sha256(path) for path in result_files},
    }
    write_json(run_dir / "manifest_final.json", manifest)
    receipt["manifest_final_sha256"] = file_sha256(run_dir / "manifest_final.json")
    write_json(lock_path, receipt)
    print(f"Avaliação final salva em: {run_dir}")
    print("2024 foi aberto uma vez. O protocolo não pode mais ser alterado.")
    print(metrics.loc[metrics["modelo_congelado"]].to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("dataset", type=Path)
    freeze_parser.add_argument(
        "--output", type=Path, default=Path("artifacts/final_evaluation")
    )
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("dataset", type=Path)
    evaluate_parser.add_argument("--run-dir", type=Path, required=True)
    evaluate_parser.add_argument("--confirm-open-2024", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "freeze":
        freeze(args.dataset, args.output)
    else:
        evaluate(args.dataset, args.run_dir, args.confirm_open_2024)


if __name__ == "__main__":
    main()
