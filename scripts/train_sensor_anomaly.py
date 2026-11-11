#!/usr/bin/env python3
"""Treina e versiona a IA exploratória da telemetria real do ESP32."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from frontend.data_access import database_url
from src.sensor_anomaly import train_model


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "sensor_anomaly")
    parser.add_argument("--reference-end", default="2026-11-04T00:00:00Z")
    return parser.parse_args()


def load_readings() -> pd.DataFrame:
    url = database_url({"TCC_DB_URL": os.getenv("TCC_DB_URL")})
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 15})
    query = text("""
        select id, device_id, data_hora, ph_value, turbidity_value,
               tds_value, temperature_value, status
        from public.leituras_sensor
        where data_hora >= timestamptz '2026-01-01'
        order by data_hora, id
    """)
    with engine.connect() as connection:
        return pd.read_sql(query, connection, parse_dates=["data_hora"])


def main():
    args = parse_args()
    result = train_model(load_readings(), reference_end=args.reference_end)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact = args.output_dir / "isolation_forest_v1.joblib"
    metrics = args.output_dir / "metrics_v1.json"
    joblib.dump(result.bundle, artifact)
    metrics.write_text(json.dumps(result.metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Artefato: {artifact}")
    print(f"Métricas: {metrics}")
    print(json.dumps(result.metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
