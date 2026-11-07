# Análise pós-hoc de 2024

Depois da abertura única do holdout, são permitidas somente análises
descritivas identificadas explicitamente como **pós-hoc**. Elas não podem
alterar o campeão, as features, os hiperparâmetros ou o limiar confirmatório.

## Objetivos

1. localizar semanas e períodos com maiores erros;
2. separar superestimação, subestimação, falsos positivos e falsos negativos;
3. interpretar os coeficientes padronizados do Poisson sem alegação causal;
4. comparar limiares apenas como sensibilidade descritiva;
5. preparar um contrato de previsões para o dashboard.

## Limiar e níveis operacionais

O alerta oficial permanece em **4 casos semanais**, valor congelado como o
terceiro quartil do alvo no desenvolvimento até 2023. Para a interface, pode
ser exibido um nível exploratório de **atenção** entre 2 e menos de 4 casos.
Essa camada não substitui o desfecho confirmado:

| Previsão | Nível exibido |
|---:|---|
| menor que 2 | normal |
| de 2 até menos de 4 | atenção |
| 4 ou mais | alerta |

## Execução

```bash
python scripts/analyze_posthoc_2024.py \
  --run-dir /caminho/para/20261016T035301Z \
  --output-dir /caminho/para/posthoc_2024
```

Antes da análise, o script verifica todos os hashes registrados no manifesto
final. Os modelos salvos são carregados apenas para leitura dos coeficientes;
não há chamada a `fit` nem seleção de nova configuração.

## Interpretação dos coeficientes

Como o pipeline padroniza as variáveis antes da regressão, `exp(coeficiente)`
representa a razão estimada entre taxas prevista para um aumento de um desvio-
padrão na feature, mantendo as demais constantes. Esse valor é associativo,
não causal. A presença de variáveis climáticas correlacionadas também faz com
que o efeito seja distribuído entre coeficientes.

## Limitações obrigatórias

- A sensibilidade de limiares foi observada depois do teste e é exploratória.
- O limiar de 4 não é clínico, diagnóstico ou normativo.
- A camada epidemiológica não demonstra que pH, turbidez ou TDS detectam a
  bactéria ou predizem diretamente a leptospirose.
- IoT, previsão epidemiológica e visualização são módulos integrados, porém
  metodologicamente distintos.
