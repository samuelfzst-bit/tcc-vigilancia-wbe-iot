# Modelagem v2 — validação temporal e sensibilidade

## Objetivo

Selecionar modelos para prever casos semanais de leptospirose em `t+1` e `t+2`
sem usar o holdout de 2024 durante desenvolvimento, ajuste ou escolha de features.

## Recortes temporais

- Validação cruzada expansiva: anos de 2018, 2019, 2020, 2021 e 2022.
- Validação final pré-teste: 2023.
- Teste bloqueado: 2024.

Em cada fold, o treino contém apenas anos anteriores ao ano avaliado. Não há
embaralhamento aleatório.

## Candidatos

- Regressão de Poisson regularizada.
- Regressão Tweedie com ligação log, incluída para avaliar sobredispersão.
- Random Forest com critério de Poisson.
- HistGradientBoosting com perda de Poisson.

A busca é pequena e auditável. Os hiperparâmetros são escolhidos pela média do
MAE nos folds de 2018–2022; RMSE e desvio do MAE são desempates.

## Baselines

- Casos conhecidos com lag 2.
- Média dos lags conhecidos 2–5.
- Lag sazonal 52.
- Média histórica do alvo por semana epidemiológica, ajustada apenas no treino.

## Métricas

- MAE: métrica principal.
- RMSE: penaliza erros grandes.
- Deviance de Poisson: aderência à distribuição de contagem.
- Viés médio: identifica superestimação ou subestimação sistemática.
- MAE em picos: usa como corte o terceiro quartil do alvo no treino de cada fold.

## Análises de sensibilidade

Os três primeiros finalistas de cada horizonte são reavaliados em:

1. histórico completo;
2. histórico climático mais estável a partir de 2015;
3. remoção de janelas longas (`lag_8`, `lag_12`, `lag_52` e agregações de 8 semanas).

## Artefatos gerados

1. métricas por fold;
2. resumo da validação cruzada;
3. hiperparâmetros selecionados;
4. métricas da validação de 2023;
5. ranking dos finalistas;
6. análise de sensibilidade;
7. previsões de 2023;
8. gráfico observado versus previsto;
9. manifesto reproduzível e relatório Markdown.

## Regra para abrir o teste

O teste de 2024 não é acessível pelo script v2. A abertura exigirá uma rotina
separada, criada somente após o registro formal do campeão, das features, dos
hiperparâmetros e da regra operacional de alerta.
