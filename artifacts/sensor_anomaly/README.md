# Artefato da IA dos sensores

- `isolation_forest_v1.joblib`: pipeline `RobustScaler + IsolationForest` usado
  pelo dashboard.
- `metrics_v1.json`: metadados, corte, parâmetros e métricas de validação.

O artefato foi treinado pelo script `scripts/train_sensor_anomaly.py` sobre a
telemetria real consultada em modo somente leitura. Para reproduzir:

```bash
TCC_DB_URL="..." python scripts/train_sensor_anomaly.py
```

O ambiente deve usar `scikit-learn==1.8.0`. O artefato detecta mudanças
multivariadas incomuns e não possui significado sanitário.
