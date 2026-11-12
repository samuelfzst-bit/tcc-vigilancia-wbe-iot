#!/usr/bin/env python3
"""Treina e avalia o challenger V2 sem versionar a telemetria bruta."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from frontend.data_access import database_url
from src.sensor_challenger_v2 import (
    challenger_bundle,
    evaluate_perturbation_grid_v2,
    temporal_validation_v2,
)
from src.sensor_validation import (
    acceptance_criteria,
    evaluate_perturbation_grid,
    temporal_validation,
)

REFERENCE_END = "2026-11-04T00:00:00Z"
OUTPUT_DIR = ROOT / "artifacts" / "sensor_anomaly"


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def load_readings(input_json: str | None) -> pd.DataFrame:
    if input_json:
        return pd.read_json(input_json)
    raw_url = os.environ.get("TCC_DB_URL")
    if not raw_url:
        raise RuntimeError("Informe --input-json ou a variável TCC_DB_URL.")
    engine = create_engine(
        database_url({"TCC_DB_URL": raw_url}),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
    )
    query = text("""
        select id, device_id, data_hora, ph_value, turbidity_value,
               tds_value, temperature_value, status
        from public.leituras_sensor
        where data_hora >= timestamptz '2026-01-01'
        order by data_hora, id
    """)
    with engine.connect() as connection:
        return pd.read_sql(query, connection, parse_dates=["data_hora"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", help="JSON temporário fora do repositório")
    args = parser.parse_args()
    readings = load_readings(args.input_json)

    v1 = temporal_validation(readings, reference_end=REFERENCE_END, train_fraction=0.8)
    v1_grid = evaluate_perturbation_grid(v1)
    v1_criteria = acceptance_criteria(v1_grid)

    v2 = temporal_validation_v2(readings, reference_end=REFERENCE_END)
    v2_grid = evaluate_perturbation_grid_v2(v2)
    v2_criteria = acceptance_criteria(v2_grid)
    bundle = challenger_bundle(v2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, OUTPUT_DIR / "extra_trees_synthetic_v2.joblib", compress=9)
    metrics = {
        **v2.summary,
        "algorithm": "ExtraTreesClassifier",
        "acceptance_passed": int(v2_criteria["passed"].sum()),
        "acceptance_total": len(v2_criteria),
        "all_offline_criteria_passed": bool(v2_criteria["passed"].all()),
        "limitations": [
            "rótulos positivos são perturbações sintéticas, não eventos físicos",
            "taxa natural não equivale a falso positivo comprovado",
            "não há interpretação sanitária ou diagnóstico de leptospirose",
            "promoção depende de ensaio físico controlado",
        ],
    }
    validation = {
        "summary": v2.summary,
        "grid": v2_grid.to_dict(orient="records"),
        "criteria": v2_criteria.to_dict(orient="records"),
    }
    comparison = {
        "same_final_test_period": True,
        "v1": {
            "model": "IsolationForest",
            "criteria_passed": int(v1_criteria["passed"].sum()),
            "criteria_total": len(v1_criteria),
            "criteria": v1_criteria.to_dict(orient="records"),
        },
        "v2": {
            "model": "ExtraTreesClassifier com perturbações sintéticas",
            "criteria_passed": int(v2_criteria["passed"].sum()),
            "criteria_total": len(v2_criteria),
            "criteria": v2_criteria.to_dict(orient="records"),
        },
        "decision": "manter V1 no dashboard até ensaio físico controlado do V2",
    }
    for filename, payload in (
        ("metrics_v2.json", metrics),
        ("validation_offline_v2.json", validation),
        ("comparison_v1_v2.json", comparison),
    ):
        (OUTPUT_DIR / filename).write_text(
            json.dumps(_json_value(payload), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(json.dumps(_json_value(metrics), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
