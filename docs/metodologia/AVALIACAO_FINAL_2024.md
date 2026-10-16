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
