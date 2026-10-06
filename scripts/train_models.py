"""Executa a comparação inicial sem abrir o teste por padrão."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

from src.modeling import evaluate_locked_test, fit_and_validate
from src.validation import validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--open-test", action="store_true", help="Avalia 2024; use só após congelar a escolha")
    args = parser.parse_args()

    data = pd.read_parquet(args.dataset)
    validate_dataset(data)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output / stamp
    run_dir.mkdir(parents=True, exist_ok=False)

    tables = []
    candidates = {}
    for horizon in (1, 2):
        for feature_set in ("epidemiologia", "clima", "combinado"):
            metrics, fitted, features = fit_and_validate(data, horizon, feature_set)
            tables.append(metrics)
            candidates[(horizon, feature_set)] = (fitted, features)

    result = pd.concat(tables, ignore_index=True)
    result.to_csv(run_dir / "metricas_validacao.csv", index=False)

    manifest = {
        "created_at_utc": stamp,
        "dataset": str(args.dataset),
        "test_opened": bool(args.open_test),
        "selection_metric": "mae",
    }

    if args.open_test:
        test_rows = []
        for horizon in (1, 2):
            subset = result.loc[(result.horizonte == horizon) & ~result.modelo.str.startswith("baseline")]
            winner = subset.sort_values(["mae", "rmse"]).iloc[0]
            fitted, features = candidates[(horizon, winner.conjunto)]
            final_model, test_result = evaluate_locked_test(
                data, horizon, winner.conjunto, winner.modelo,
                fitted[winner.modelo], features,
            )
            joblib.dump(final_model, run_dir / f"modelo_h{horizon}.joblib")
            test_rows.append(test_result.__dict__)
        pd.DataFrame(test_rows).to_csv(run_dir / "metricas_teste.csv", index=False)

    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Execução salva em {run_dir}")


if __name__ == "__main__":
    main()
