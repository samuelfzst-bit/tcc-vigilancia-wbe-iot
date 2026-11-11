# Resultado da validação offline da IA dos sensores

## Conclusão executiva

O modelo `sensor_iforest_delta_v1_20261111` passou em 5 dos 7 critérios definidos
antes da execução. O resultado sustenta a integração técnica IoT → IA como prova
de conceito, mas não autoriza apresentar o detector como validado para cada sensor.
Permanecem pendentes a sensibilidade de pH, a sensibilidade de TDS e o ensaio
físico controlado.

## Barreira temporal

- referência: 1.263 mudanças válidas;
- ajuste: 1.010 mudanças iniciais;
- validação: 253 mudanças posteriores;
- fim do ajuste: 08/10/2026 03:52:21 UTC;
- início da validação: 08/10/2026 03:52:24 UTC;
- fim da validação: 10/10/2026 21:35:25 UTC.

Não houve sobreposição temporal entre ajuste e validação.

## Critérios

| Critério pré-definido | Observado | Meta | Resultado |
|---|---:|---:|---|
| Taxa sinalizada natural | 5,14% | ≤ 10% | passou |
| Multivariado moderado | 100,00% | ≥ 70% | passou |
| Multivariado forte | 100,00% | ≥ 90% | passou |
| pH forte | 43,08% | ≥ 50% | **não passou** |
| Turbidez forte | 70,36% | ≥ 50% | passou |
| TDS forte | 9,09% | ≥ 50% | **não passou** |
| Temperatura forte | 51,38% | ≥ 50% | passou |

## Interpretação correta

A taxa natural de 5,14% descreve quantas mudanças sem perturbação artificial foram
sinalizadas; não é taxa comprovada de falso positivo, pois não há rótulos de campo.
As taxas sintéticas medem resposta a alterações conhecidas adicionadas aos dados;
não são precisão, recall sanitário ou capacidade de detectar leptospirose.

O resultado multivariado é forte, coerente com o objetivo do Isolation Forest.
Entretanto, a resposta isolada de TDS é insuficiente e a de pH ficou abaixo da meta.
Portanto, a versão atual deve permanecer identificada como **detector multivariado
exploratório**.

## Próxima decisão

1. executar o notebook no Colab e preservar os outputs;
2. realizar o ensaio físico com intervenções registradas por horário;
3. medir detecção por evento, tempo de resposta e sinalizações em período estável;
4. comparar a versão atual com uma candidata recalibrada, sem substituir o modelo
   atual antes da comparação temporal;
5. somente promover uma nova versão se houver ganho mensurável e reproduzível.
