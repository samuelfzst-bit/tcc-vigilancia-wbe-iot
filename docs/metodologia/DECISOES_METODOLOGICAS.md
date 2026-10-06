# Registro de decisões metodológicas

Atualizado em 2026-10-03. Este documento registra decisões do estudo; não é uma tabela operacional do Supabase.

| Tema | Decisão | Justificativa |
| --- | --- | --- |
| Desfecho | Casos semanais confirmados de leptospirose | Associação plausível com chuva, alagamentos e saneamento; melhor aderência ao argumento urbano do protótipo que dengue. |
| Geografia principal | Município de São Paulo | Mantém coerência entre casos, estação meteorológica A701 e capacidade de execução. Ampliação geográfica exigiria novas estações e modelagem espacial. |
| Cenário | Residentes, excluindo importados conhecidos | Reduz atribuição indevida de exposição externa ao clima local. Cenários alternativos ficam apenas para sensibilidade. |
| Disponibilidade | `DT_ENCERRA` | Aproxima o momento em que a confirmação estaria utilizável. `DT_NOTIFIC` foi descartada como proxy principal. |
| Frequência | Semana epidemiológica | Compatível com baixa contagem diária e com a disponibilidade dos dados. |
| Horizontes | `t+1` e `t+2` | Entrega antecedência operacional mensurável sem extrapolação excessiva. |
| Divisão | Treino até 2022, validação 2023, teste 2024 | Preserva ordem temporal e mantém um período final intocado. |
| IoT | Camada física operacional separada do treino histórico | Não existe série longitudinal real dos sensores para sustentar sua inclusão no modelo. Integração ocorre na aplicação e é avaliada por métricas próprias. |
| Modelos | Poisson, HistGradientBoosting Poisson e Random Forest Poisson | Comparam modelo regularizado e não linear; Random Forest não é presumido vencedor. |
| Métrica principal | MAE | Interpretação direta em casos por semana. RMSE e Poisson deviance são complementares. |
| Banco oficial | Supabase/PostgreSQL | Evita fontes de verdade concorrentes; Docker local mantém somente MQTT. |

## Regras de governança experimental

1. Ajustar imputação, escala e seleção somente no treino de cada experimento.
2. Escolher arquitetura e limiar com treino/validação; abrir 2024 uma única vez.
3. Comparar todo modelo com `lag_2`, média dos lags 2–5 e `lag_52`.
4. Executar ablação: epidemiologia, clima e combinado.
5. Registrar commit, versão do dataset, SHA-256, seed e métricas de cada execução.
6. Não interpretar associação preditiva como causalidade.
## 2026-10-06 — modelagem v2

- Manter 2024 bloqueado para avaliação final única.
- Selecionar hiperparâmetros em folds temporais expansivos de 2018 a 2022.
- Usar 2023 como validação final pré-teste.
- Manter MAE como métrica principal; RMSE, estabilidade e MAE em picos como critérios auxiliares.
- Incluir Tweedie para avaliar sobredispersão, sem presumir que vencerá o modelo mais simples.
- Executar sensibilidade ao período de cobertura climática e às janelas longas.
- Não criar um modelo supervisionado de qualidade da água sem rótulos laboratoriais.
