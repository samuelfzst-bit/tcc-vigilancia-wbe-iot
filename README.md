# Vigilância epidemiológica urbana com IoT e IA

Protótipo de TCC para antecipação semanal do risco de leptospirose em São Paulo. O projeto combina dados epidemiológicos do SINAN, clima do INMET, uma camada física IoT e modelos de aprendizado de máquina.

## Escopo metodológico

- Doença-alvo: leptospirose.
- Unidade temporal: semana epidemiológica.
- Horizontes: `t+1` e `t+2` semanas.
- Cenário principal: casos confirmados de residentes de São Paulo, excluindo casos importados conhecidos.
- Disponibilidade epidemiológica: `DT_ENCERRA`.
- Divisão temporal fixa: treino até 2022, validação em 2023 e teste final em 2024.
- Banco oficial do projeto: Supabase/PostgreSQL.

O IoT é uma camada física real de aquisição e transmissão. Como ainda não existe uma série histórica longitudinal dos sensores compatível com o SINAN/INMET, suas leituras não serão usadas para treinar o modelo epidemiológico histórico. As camadas são integradas na aplicação, mas avaliadas separadamente.

## Estrutura

```text
notebooks/       extração, auditoria e experimentos reproduzíveis
src/             contratos e código reutilizável
sql/             views privadas de clima e modelagem no Supabase
tests/           testes automáticos de qualidade e antileakage
iot_simulator/   publicação MQTT e apoio à validação do hardware
docs/            decisões e documentação metodológica
artifacts/       convenção para métricas e modelos, sem binários no Git
```

## Começo rápido

Consulte [QUICKSTART.md](QUICKSTART.md). O primeiro passo da modelagem é executar `notebooks/01_extracao_e_auditoria.ipynb`, nunca o notebook legado arquivado.

## Equipe

- Samuel: ciência de dados e modelagem.
- Larissa: análise de dados e Supabase.
- Gustavo: análise de dados e protótipo físico.
- Leonardo: infraestrutura e protótipo físico.

## Segurança e dados

Credenciais ficam apenas em variáveis de ambiente ou no gerenciador de segredos do Colab. Microdados do SINAN, snapshots Parquet e modelos treinados não devem ser versionados.

Este repositório faz parte de um Trabalho de Conclusão de Curso.
