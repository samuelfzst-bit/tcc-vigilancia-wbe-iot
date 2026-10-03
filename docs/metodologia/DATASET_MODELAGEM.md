# Dataset de modelagem do TCC

## Objetivo

Prever a quantidade semanal de casos confirmados de leptospirose em São Paulo capital com antecedência de uma (`t+1`) ou duas semanas (`t+2`), usando somente informações que seriam conhecidas no domingo da semana de origem.

## Objeto oficial

- Visão: `tcc_private.dataset_modelagem`
- Versão: `dataset_modelagem_v1_20260927`
- Cenário principal: `principal_sem_importados_conhecidos`
- Linhas: 1.561
- Colunas: 64
- Chave lógica: `(horizonte, inicio_semana_t)`
- Acesso: privado; leitura pelo `service_role`

## Particionamento temporal

| Split | Regra pelo ano do alvo | t+1 | t+2 |
| --- | --- | ---: | ---: |
| Treino | até 2022 | 677 | 676 |
| Validação | 2023 | 52 | 52 |
| Teste | 2024 | 52 | 52 |

O teste de 2024 não pode participar de imputação, escala, seleção de variáveis, ajuste de hiperparâmetros, escolha de modelo, calibração ou definição do limiar de alerta.

## Grupos de variáveis

### Identificação e auditoria

Horizonte, datas de origem/corte/alvo, ano e semana do alvo, split, cenário, fonte de disponibilidade e versões das bases.

### Alvo

`target_casos`: contagem final de casos na semana futura. Nunca deve entrar em `X` nem participar de qualquer transformação dos preditores.

### Epidemiologia disponível no corte

Contagens conhecidas pelos lags 0, 1, 2, 3, 4, 5, 8, 12 e 52. A disponibilidade usa `DT_ENCERRA` em 100% dos 2.726 registros elegíveis. Também há média, soma, máximo e tendência dos lags 2–5.

### Clima observado até a origem

Temperatura, umidade, precipitação e vento da semana `t`; lags climáticos selecionados; precipitação acumulada em 2, 4 e 8 semanas; médias móveis de temperatura e umidade em 4 e 8 semanas.

As janelas exigem cobertura integral. Se algum componente estiver ausente, o agregado permanece nulo. Ausência nunca é convertida em chuva zero.

### Sazonalidade

Seno e cosseno da semana epidemiológica do alvo. A data futura é conhecida no momento da previsão, mas nenhuma medição climática ou epidemiológica futura é utilizada.

## Proteções contra leakage

1. Data de corte sempre igual ao último dia da semana de origem.
2. Alvo exatamente 7 ou 14 dias após a origem.
3. Casos recentes representam apenas confirmações encerradas até o corte.
4. Clima limitado à semana de origem e anteriores.
5. Imputadores, escaladores e seleção de features ajustados somente no treino de cada dobra.
6. Teste de 2024 usado uma única vez, após congelar pipeline, hiperparâmetros e eventual calibração.
7. Cenários geográficos de sensibilidade não entram no treino principal.

## Estratégia de experimentação

Treinar separadamente `t+1` e `t+2` e comparar três conjuntos de variáveis:

1. Epidemiologia apenas.
2. Clima apenas.
3. Epidemiologia + clima.

Essa ablação mede se o clima agrega valor real. O IoT não será artificialmente misturado ao histórico: como não existe série histórica dos sensores físicos, ele compõe a camada operacional do protótipo e pode gerar indicadores em tempo real, mas não será apresentado como preditor historicamente treinado sem evidência.

## Modelos candidatos

- Baselines já registrados: `lag_2`, média dos lags 2–5 e sazonal `lag_52`.
- Regressão de Poisson regularizada.
- Modelo de contagem com sobredispersão, como Binomial Negativa.
- HistGradientBoosting com perda de Poisson.
- Random Forest como comparação não linear.
- XGBoost/LightGBM com objetivo de contagem, se a dependência for estabilizada no ambiente.

A média do alvo no treino é aproximadamente 3,34 e o desvio 3,77; a variância superior à média exige comparar modelos que tratem sobredispersão. Random Forest não deve ser escolhido por preferência prévia.

## Avaliação

- MAE como métrica principal de erro interpretável.
- RMSE para penalizar erros grandes.
- Poisson deviance para adequação a contagens.
- Erro dos picos e recall de semanas de alto risco, depois de definir o limiar somente no desenvolvimento.
- Comparação obrigatória com baselines.
- Validação temporal com janela expansiva dentro de 2010–2022.
- 2023 para seleção final/calibração; 2024 para teste final intocado.

Para previsão de contagem, avaliar calibração por faixas de valor previsto e cobertura de intervalos. Platt e isotonic só entram se for formalizada uma saída classificatória de alerta; o calibrador nunca será ajustado no teste.

## Próximas entregas

1. Notebook de auditoria e treino reproduzível.
2. Relatório de drift e missingness por split.
3. Resultados de baselines e modelos candidatos para `t+1` e `t+2`.
4. Estudo de ablação clima × epidemiologia × combinado.
5. Calibração e limiar operacional somente após selecionar o tipo de saída final.
