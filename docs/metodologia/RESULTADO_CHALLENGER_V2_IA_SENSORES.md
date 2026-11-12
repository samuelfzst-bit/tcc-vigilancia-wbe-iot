# Resultado do challenger V2 da IA dos sensores

## Decisão executiva

O `sensor_extratrees_synthetic_v2_20261111` passou nos sete critérios offline e
superou o Isolation Forest V1 no mesmo período final de teste. Ele é, portanto, o
candidato recomendado para o ensaio físico controlado. O V1 continua ativo no
dashboard: o V2 **não foi promovido**, porque seus exemplos positivos são
perturbações sintéticas e ainda não existem rótulos de eventos físicos reais.

## Desenho sem vazamento temporal

A referência contém 1.263 mudanças válidas anteriores a 04/11/2026 e foi separada
cronologicamente, antes do ajuste:

| Bloco | Linhas naturais | Uso |
|---|---:|---|
| Ajuste | 757 | naturais + perturbações sintéticas aleatórias |
| Calibração | 253 | definir o limiar no percentil 95 das probabilidades naturais |
| Teste final | 253 | medir taxa natural e grade fixa; nunca participa do ajuste |

O ajuste terminou em 08/10/2026 02:33:33 UTC. A calibração começou depois desse
horário e terminou em 08/10/2026 03:52:21 UTC. O teste começou em seguida e foi até
10/10/2026 21:35:25 UTC. Não há sobreposição entre os três blocos.

As magnitudes positivas do treino são sorteadas em intervalos contínuos. A grade
fixa de teste é aplicada apenas ao bloco final. Isso reduz, mas não elimina, o risco
de o resultado refletir a regra usada para gerar exemplos artificiais.

## Resultado nos critérios definidos anteriormente

| Critério | V1 | V2 | Meta | V2 passou? |
|---|---:|---:|---:|:---:|
| Taxa sinalizada natural | 5,14% | 3,16% | ≤ 10% | sim |
| Multivariado moderado | 100,00% | 100,00% | ≥ 70% | sim |
| Multivariado forte | 100,00% | 100,00% | ≥ 90% | sim |
| pH forte | 43,08% | 100,00% | ≥ 50% | sim |
| Turbidez forte | 70,36% | 100,00% | ≥ 50% | sim |
| TDS forte | 9,09% | 100,00% | ≥ 50% | sim |
| Temperatura forte | 51,38% | 100,00% | ≥ 50% | sim |

Na grade ampliada, a resposta do V2 aumentou de forma coerente com a intensidade:

- pH: 3,16% em 0,25; 6,72% em 0,5; 99,60% em 1; 100% em 2 e 3;
- turbidez: 26,88% em 2 e 100% a partir de 5;
- TDS: 15,02% em 2; 97,23% em 5; 100% a partir de 10;
- temperatura: 9,09% em 0,25 e 100% a partir de 0,5;
- multivariado: 100% nas escalas 0,25, 0,5 e 1,0.

## O que essas métricas significam

`Detection rate` é a proporção de exemplos artificialmente alterados que o modelo
sinalizou. Não é acurácia sanitária, precisão, recall de eventos reais nem prova de
detecção de leptospirose. A taxa natural também não é falso positivo comprovado,
porque o período não foi rotulado por um especialista como livre de alterações.

O Extra Trees foi escolhido em vez do Random Forest testado na prototipação porque
apresentou resposta monotônica por intensidade. O Random Forest também passou nos
critérios agregados, mas sua detecção de pH caiu na maior magnitude, comportamento
indesejável para extrapolação.

## Regra de promoção

O V2 só deve substituir o V1 após um ensaio físico com:

1. período estável de controle;
2. intervenções separadas em pH, turbidez, TDS e temperatura;
3. horários de início e fim registrados antes de consultar a saída do modelo;
4. medição de detecção por evento, tempo até o alerta e alertas no controle;
5. comparação V1 × V2 nas mesmas janelas.

Até essa etapa, a formulação correta é: **o V2 passou na validação offline de
sensibilidade sintética e aguarda validação física**.
