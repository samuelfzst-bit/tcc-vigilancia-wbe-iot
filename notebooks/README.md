# Notebooks

Ordem oficial:

1. `01_extracao_e_auditoria.ipynb`: consulta a view privada, valida o contrato temporal e gera snapshot versionado.
2. `02_modelagem_v2_colab.ipynb`: executa validação temporal, seleção de hiperparâmetros e sensibilidade sobre o snapshot aprovado.
3. `03_xgboost_challenger_colab.ipynb`: compara Poisson e XGBoost com regra de substituição pré-registrada, sem abrir 2024.

O treino v2 usa `scripts/train_models_v2.py`. O script não possui opção para abrir
o teste de 2024 e salva os resultados em `MyDrive/TCC/model_runs_v2`.

O challenger usa `scripts/run_xgboost_challenger.py` e salva os resultados em
`MyDrive/TCC/xgboost_challenger`. Ele também não possui rotina para abrir 2024.

O notebook anterior foi preservado em `archive/` apenas para rastreabilidade. Ele não deve ser usado porque antecede as decisões atuais de cenário, disponibilidade e split.
