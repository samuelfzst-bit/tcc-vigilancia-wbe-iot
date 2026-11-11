# Protocolo de validação da IA dos sensores

## Objetivo

Verificar, de maneira reproduzível, se o Isolation Forest reage a mudanças
conhecidas sem transformar o experimento em evidência sanitária. O protocolo tem
duas etapas: validação offline com perturbações controladas e ensaio físico com o
protótipo.

## Etapa 1 — validação offline

1. Consultar `public.leituras_sensor` em modo somente leitura.
2. Remover horários anteriores a 2026, duplicidades e pares separados por mais de
   7min30s.
3. Manter o corte de referência em 04/11/2026 00:00 UTC.
4. Ajustar o modelo nos 80% iniciais e avaliar nos 20% finais.
5. Medir a taxa sinalizada na validação natural.
6. Inserir mudanças artificiais de diferentes intensidades, uma variável por vez.
7. Repetir com mudanças simultâneas nas quatro variáveis.

### Grade pré-definida

| Sensor | Magnitudes testadas |
|---|---|
| pH | ±0,25; ±0,5; ±1; ±2; ±3 |
| Turbidez | ±2; ±5; ±10; ±20; ±40 |
| TDS | ±2; ±5; ±10; ±25; ±50 |
| Temperatura | ±0,25; ±0,5; ±1; ±2; ±4 |
| Multivariado | 25%, 50% e 100% das magnitudes máximas |

### Critérios definidos antes da execução

- taxa sinalizada natural ≤ 10%;
- cenário multivariado moderado com detecção ≥ 70%;
- cenário multivariado forte com detecção ≥ 90%;
- cenário forte isolado de cada sensor com detecção ≥ 50%.

Reprovar um critério não deve ser escondido. O resultado orienta recalibração,
troca de variáveis ou redução do escopo declarado.

## Etapa 2 — ensaio físico controlado

O grupo deve realizar uma sequência estável e depois uma intervenção por sensor,
registrando manualmente o início e o fim. Utilizar somente procedimentos seguros e
compatíveis com o manual de cada componente.

Sequência sugerida:

1. 15 minutos de condição estável para formar referência operacional.
2. Alteração controlada de pH usando soluções de calibração conhecidas.
3. Alteração de turbidez com amostra preparada e homogênea.
4. Alteração de TDS com solução de condutividade conhecida.
5. Alteração de temperatura com amostras em temperaturas medidas externamente.
6. Um cenário combinado, somente após os testes individuais.

Para cada evento, registrar `event_id`, `start_at`, `end_at`, `expected_sensor`,
descrição, valor de referência externo e observações. Não registrar senhas ou
credenciais.

## Métricas do ensaio físico

- evento detectado: ao menos uma sinalização dentro da janela;
- tempo até a primeira sinalização;
- quantidade de sinalizações dentro do evento;
- taxa sinalizada nos períodos estáveis anteriores;
- consistência entre sensor esperado e maior mudança indicada.

O ensaio não comprova detecção de leptospirose ou qualidade da água. Ele comprova
somente que o fluxo sensor → banco → IA responde a intervenções conhecidas.
