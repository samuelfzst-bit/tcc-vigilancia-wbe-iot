# Protocolo do challenger XGBoost

## Objetivo

Responder de forma controlada se um modelo de árvores impulsionadas acrescenta
ganho relevante sobre a Regressão de Poisson regularizada já selecionada.
O experimento não reabre a busca geral de modelos e não consulta 2024.

## Hipótese e comparação justa

- Campeão atual: Regressão de Poisson, `alpha=1`.
- Challenger: `XGBRegressor` 3.0.5 com `objective="count:poisson"`.
- Features: conjunto `clima`, incluindo os termos sazonais, idêntico nos dois modelos.
- Folds de seleção: validação expansiva em 2018, 2019, 2020, 2021 e 2022.
- Validação final: 2023.
- Teste bloqueado: 2024.
- Métrica principal: MAE.

## Grade pré-especificada

A grade contém somente oito configurações:

- `n_estimators`: 200 ou 400;
- `max_depth`: 2 ou 3;
- `learning_rate`: 0,03 ou 0,05.

Parâmetros fixos:

- `min_child_weight=5`;
- `subsample=0.8`;
- `colsample_bytree=0.8`;
- `reg_alpha=0`;
- `reg_lambda=10`;
- `tree_method="hist"`;
- `random_state=42`.

Essas restrições reduzem a capacidade de memorizar uma série semanal pequena.
A configuração do XGBoost é escolhida exclusivamente pelo MAE médio dos folds
2018–2022, com RMSE e desvio do MAE como desempates.

## Regra de substituição pré-registrada

O XGBoost só substitui o Poisson em determinado horizonte se cumprir
simultaneamente:

1. reduzir o MAE de 2023 em pelo menos 5%;
2. não piorar o MAE médio da validação temporal 2018–2022;
3. manter o desvio do MAE entre folds em até 1,25 vez o desvio do Poisson;
4. manter o MAE dos picos de 2023 em até 1,10 vez o MAE de picos do Poisson.

Se qualquer condição falhar, o Poisson permanece por parcimônia,
interpretabilidade e menor risco de sobreajuste.

## Integridade metodológica

- A escolha pode ser diferente para `t+1` e `t+2`.
- Não serão adicionadas novas configurações depois de observar 2023.
- O teste de 2024 não será carregado, avaliado ou usado na decisão.
- Depois da decisão, modelo, features, hiperparâmetros e limiar de alerta serão
  registrados em um manifesto de congelamento.
- Um resultado desfavorável no teste final não autoriza trocar o modelo.

## Execução

Use `notebooks/03_xgboost_challenger_colab.ipynb` ou:

```bash
python scripts/run_xgboost_challenger.py CAMINHO_DO_DATASET --output artifacts/xgboost_challenger
```

O diretório de saída contém métricas por fold, configuração escolhida, métricas
de 2023, decisão automática, previsões, gráfico, manifesto e resumo executivo.
# Protocolo do challenger XGBoost

## Objetivo

Responder de forma controlada se um modelo de árvores impulsionadas acrescenta
ganho relevante sobre a Regressão de Poisson regularizada já selecionada.
O experimento não reabre a busca geral de modelos e não consulta 2024.

## Hipótese e comparação justa

- Campeão atual: Regressão de Poisson, `alpha=1`.
- Challenger: `XGBRegressor` 3.0.5 com `objective="count:poisson"`.
- Features: conjunto `clima`, incluindo os termos sazonais, idêntico nos dois modelos.
- Folds de seleção: validação expansiva em 2018, 2019, 2020, 2021 e 2022.
- Validação final: 2023.
- Teste bloqueado: 2024.
- Métrica principal: MAE.

## Grade pré-especificada

A grade contém somente oito configurações:

- `n_estimators`: 200 ou 400;
- `max_depth`: 2 ou 3;
- `learning_rate`: 0,03 ou 0,05.

Parâmetros fixos:

- `min_child_weight=5`;
- `subsample=0.8`;
- `colsample_bytree=0.8`;
- `reg_alpha=0`;
- `reg_lambda=10`;
- `tree_method="hist"`;
- `random_state=42`.

Essas restrições reduzem a capacidade de memorizar uma série semanal pequena.
A configuração do XGBoost é escolhida exclusivamente pelo MAE médio dos folds
2018–2022, com RMSE e desvio do MAE como desempates.

## Regra de substituição pré-registrada

O XGBoost só substitui o Poisson em determinado horizonte se cumprir
simultaneamente:

1. reduzir o MAE de 2023 em pelo menos 5%;
2. não piorar o MAE médio da validação temporal 2018–2022;
3. manter o desvio do MAE entre folds em até 1,25 vez o desvio do Poisson;
4. manter o MAE dos picos de 2023 em até 1,10 vez o MAE de picos do Poisson.

Se qualquer condição falhar, o Poisson permanece por parcimônia,
interpretabilidade e menor risco de sobreajuste.

## Integridade metodológica

- A escolha pode ser diferente para `t+1` e `t+2`.
- Não serão adicionadas novas configurações depois de observar 2023.
- O teste de 2024 não será carregado, avaliado ou usado na decisão.
- Depois da decisão, modelo, features, hiperparâmetros e limiar de alerta serão
  registrados em um manifesto de congelamento.
- Um resultado desfavorável no teste final não autoriza trocar o modelo.

## Execução

Use `notebooks/03_xgboost_challenger_colab.ipynb` ou:

```bash
python scripts/run_xgboost_challenger.py CAMINHO_DO_DATASET --output artifacts/xgboost_challenger
```

O diretório de saída contém métricas por fold, configuração escolhida, métricas
de 2023, decisão automática, previsões, gráfico, manifesto e resumo executivo.
