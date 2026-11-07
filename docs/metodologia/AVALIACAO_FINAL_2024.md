# Avaliação final bloqueada de 2024

## Decisão congelada

A decisão foi tomada sem consultar o holdout de 2024:

- modelo para `t+1`: Regressão de Poisson, `alpha=1`;
- modelo para `t+2`: Regressão de Poisson, `alpha=1`;
- features: conjunto `clima`, com termos sazonais;
- treino final: observações de 2010 a 2023;
- teste final: 2024, aberto uma única vez;
- métrica principal: MAE.

O XGBoost não substituiu o Poisson porque a melhora do MAE em 2023 foi de
apenas 2,0% em `t+1` e 1,8% em `t+2`, abaixo do mínimo pré-registrado de 5%.
Além disso, o challenger apresentou maior instabilidade em `t+1`.

## Regra de alerta

O alerta operacional do protótipo é disparado quando a previsão semanal é
maior ou igual ao terceiro quartil dos casos observados no desenvolvimento
até 2023, arredondado para cima. O valor é calculado e registrado no manifesto
antes de abrir 2024.

No snapshot oficial, o terceiro quartil foi igual a 4 casos para os dois
horizontes. Portanto, o limiar congelado é de **4 casos semanais** tanto para
`t+1` quanto para `t+2`.

Esse corte representa **incidência semanal historicamente elevada no
protótipo**. Ele não é um limiar clínico, diagnóstico ou normativo de saúde
pública.

## Abertura em duas fases

O notebook `04_avaliacao_final_2024_colab.ipynb` executa duas fases separadas:

1. **Congelamento:** valida o snapshot, registra modelo, features,
   hiperparâmetros, regra de alerta e hashes. O alvo de 2024 não participa de
   nenhum cálculo do protocolo.
2. **Avaliação:** exige confirmação literal, verifica a integridade do
   manifesto e abre 2024. Um recibo persistente impede uma nova execução para
   o mesmo dataset.

Depois da abertura, o modelo não pode ser alterado. Análises posteriores
devem ser identificadas como pós-hoc e não integram a avaliação confirmatória.

## Métricas finais

- MAE, com intervalo descritivo de 95% por bootstrap circular em blocos de
  quatro semanas;
- RMSE e deviance de Poisson;
- viés médio e razão entre média prevista e média observada;
- MAE nas semanas de alta incidência;
- precisão, recall, F1, especificidade e acurácia balanceada do alerta.

Baselines são calculados somente para contextualizar o desempenho. Eles não
podem substituir o campeão após a abertura do holdout.

## Artefatos

O diretório final contém:

1. protocolo pré-teste e seu hash;
2. métricas do teste de 2024;
3. métricas do alerta;
4. previsões semanais;
5. gráfico observado versus previsto;
6. modelos Poisson ajustados para `t+1` e `t+2`;
7. recibo da abertura única;
8. resumo Markdown e manifesto final com hashes dos arquivos.

## Resultado observado no holdout

A execução oficial `20261016T035301Z`, vinculada ao commit `6f18032`, foi
concluída com o repositório limpo e todos os artefatos registrados no manifesto.

| Horizonte | MAE | IC95% descritivo | RMSE | Viés | Razão de calibração |
|---:|---:|---:|---:|---:|---:|
| `t+1` | 1,368 | [0,976; 1,875] | 1,796 | +0,297 | 1,111 |
| `t+2` | 1,359 | [0,951; 1,898] | 1,896 | +0,310 | 1,116 |

O modelo superou o baseline mais competitivo, a média histórica da semana,
em aproximadamente 14,6% no MAE de `t+1` e 14,7% no MAE de `t+2`. Essas são
reduções observadas; não foi calculado um intervalo pareado para afirmar
superioridade estatística.

No alerta congelado de 4 casos, `t+1` apresentou precisão de 0,800, recall de
0,857 e F1 de 0,828. Para `t+2`, os três indicadores foram 0,714. O segundo
horizonte é tratado como complementar por carregar maior incerteza operacional.

O ano de 2024 apresentou média, variabilidade e pico inferiores aos de 2023.
Por isso, erros menores no teste não devem ser descritos isoladamente como
"melhora do modelo". A conclusão aceita é que houve generalização temporal e
ganho observado contra os baselines no período reservado.

## Continuação pós-teste

O notebook `05_analise_pos_hoc_2024_colab.ipynb` produz análise de erros,
sensibilidade de limiares e interpretação dos coeficientes. O corte de 2 casos
é usado somente como nível exploratório de atenção na interface. A avaliação
confirmatória e o alerta oficial continuam usando o limiar congelado de 4.
