# IA exploratória dos sensores

## Papel no sistema

Esta IA cria uma integração direta e verificável entre o protótipo IoT e um
algoritmo de aprendizado de máquina. Ela analisa a telemetria real persistida em
`public.leituras_sensor`. Seu objetivo é detectar mudanças multivariadas incomuns
no comportamento do protótipo — não estimar casos de leptospirose.

O modelo epidemiológico Poisson permanece independente e usa SINAN e INMET. Essa
separação evita combinar séries com frequências, coberturas e significados
diferentes.

## Auditoria e referência

- Foram recuperadas 1.570 leituras com data válida em 2026.
- Horários duplicados são deduplicados mantendo o registro de maior `id`.
- A diferença não é calculada entre dispositivos nem após lacunas superiores a
  7min30s.
- O corte da referência foi fixado em `2026-11-04T00:00:00Z`.
- Após as regras de elegibilidade, 1.263 mudanças compuseram a referência.
- Dez registros com data de época Unix de 1970 ficaram fora da extração de treino.

## Variáveis e prevenção de leakage

Para cada leitura elegível, as quatro entradas são calculadas apenas com a leitura
atual e a imediatamente anterior:

```text
delta_ph, delta_turbidez, delta_tds, delta_temperatura
```

Não são usados valores futuros. A divisão de avaliação respeita a ordem temporal:
80% iniciais para ajuste e 20% finais para validação. O artefato operacional é
então reajustado sobre toda a referência anterior ao corte.

## Algoritmo

- `RobustScaler` para reduzir influência de escala;
- `IsolationForest` com 400 árvores;
- `contamination=0,01`;
- `random_state=20261111`;
- artefato `sensor_iforest_delta_v1_20261111`.

Um escore de anomalia acima de zero corresponde à fronteira aprendida pelo
modelo. Quanto maior, mais incomum é o vetor de mudanças para a referência. O
escore não é probabilidade.

## Validação registrada

| Indicador | Resultado |
|---|---:|
| Linhas de referência | 1.263 |
| Ajuste da avaliação | 1.010 |
| Validação temporal | 253 |
| Taxa sinalizada na validação natural | 5,14% |
| Sensibilidade sintética — pH | 43,08% |
| Sensibilidade sintética — turbidez | 70,36% |
| Sensibilidade sintética — TDS | 9,09% |
| Sensibilidade sintética — temperatura | 51,38% |
| Sensibilidade sintética — multivariada | 100,00% |

As perturbações sintéticas foram de ±3 para pH, ±40 para turbidez, ±50 para TDS
e ±4 para temperatura. Elas testam resposta técnica do detector e não representam
eventos reais ou limites sanitários.

## Limitações obrigatórias de interpretação

Não existem rótulos de campo que indiquem contaminação, falha ou presença de
patógeno. Portanto, não se reportam acurácia, precisão, recall ou F1 como métricas
sanitárias. A sensibilidade isolada para TDS foi baixa e permanece registrada como
limitação. O resultado correto é **alteração multivariada incomum em relação ao
histórico do protótipo**.

Uma sinalização não prova piora da água; ausência de sinalização não prova
normalidade. O modelo deve ser recalibrado quando houver série mais longa,
calibração física consolidada e eventos rotulados.

## Operação no dashboard

O dashboard consulta `leituras_sensor` com um usuário PostgreSQL somente leitura,
carrega o artefato versionado e executa a inferência em memória. Nenhuma nova
tabela foi criada e nenhum resultado é gravado no Supabase. Essa decisão reduz o
risco operacional e preserva o fluxo já validado do protótipo.
