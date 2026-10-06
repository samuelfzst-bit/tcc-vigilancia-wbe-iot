# Notebooks

Ordem oficial:

1. `01_extracao_e_auditoria.ipynb`: consulta a view privada, valida o contrato temporal e gera snapshot versionado.
2. `02_modelagem_v2_colab.ipynb`: executa validação temporal, seleção de hiperparâmetros e sensibilidade sobre o snapshot aprovado.

O treino v2 usa `scripts/train_models_v2.py`. O script não possui opção para abrir
o teste de 2024 e salva os resultados em `MyDrive/TCC/model_runs_v2`.

O notebook anterior foi preservado em `archive/` apenas para rastreabilidade. Ele não deve ser usado porque antecede as decisões atuais de cenário, disponibilidade e split.
