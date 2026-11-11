# Artefato da IA dos sensores

- `isolation_forest_v1.joblib`: pipeline `RobustScaler + IsolationForest` usado
  pelo dashboard.
- `metrics_v1.json`: metadados, corte, parâmetros e métricas de validação.
- `validation_offline_v1.json`: critérios pré-definidos e resultado da grade de
  perturbações por intensidade.

O artefato foi treinado pelo script `scripts/train_sensor_anomaly.py` sobre a
telemetria real consultada em modo somente leitura. Para reproduzir:

```bash
TCC_DB_URL="..." python scripts/train_sensor_anomaly.py
```

O ambiente deve usar `scikit-learn==1.8.0`. O artefato detecta mudanças
multivariadas incomuns e não possui significado sanitário.

O notebook reproduzível está em `notebooks/04_validacao_ia_sensores.ipynb`. A
execução offline passou em 5 de 7 critérios; pH e TDS permaneceram abaixo das
metas e exigem revisão e ensaio físico controlado.
