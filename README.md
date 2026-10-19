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

## Resultado final de modelagem

O campeão pré-registrado foi a regressão de Poisson regularizada (`alpha=1`).
No holdout temporal único de 2024, o MAE foi de **1,368 caso/semana em `t+1`**
e **1,359 em `t+2`**, com redução observada de aproximadamente 15% contra o
baseline sazonal mais competitivo. O limiar principal pré-especificado
permanece em 4 casos semanais; previsões entre 2 e menos de 4 podem ser exibidas
apenas como nível exploratório de atenção. Esse limiar pertence ao protótipo
acadêmico e não constitui um alerta oficial de saúde pública.

Consulte `docs/metodologia/AVALIACAO_FINAL_2024.md` e
`docs/metodologia/ANALISE_POS_HOC_2024.md` para resultados e limitações.

## Executar o dashboard

O dashboard integrado usa Streamlit e consulta somente as tabelas autorizadas
do Supabase. A credencial nunca deve ser salva no Git.

```bash
python -m venv .venv
pip install -r requirements/frontend.txt
streamlit run frontend/app.py
```

Antes da execução, cada integrante deve criar localmente
`frontend/.streamlit/secrets.toml` a partir do arquivo de exemplo e receber uma
URI PostgreSQL de **somente leitura** por canal privado.

Consulte o passo a passo completo, incluindo Windows/PowerShell, Linux/macOS e
solução de erros comuns, em
[docs/EXECUTAR_DASHBOARD.md](docs/EXECUTAR_DASHBOARD.md).

As previsões atualmente exibidas são resultados retrospectivos do holdout de
2024. A telemetria IoT é um módulo físico separado; a previsão operacional
recente ainda está em desenvolvimento.

## Equipe

- Samuel: ciência de dados e modelagem.
- Larissa: análise de dados e Supabase.
- Gustavo: análise de dados e protótipo físico.
- Leonardo: infraestrutura e protótipo físico.

## Segurança e dados

Credenciais ficam apenas em variáveis de ambiente ou no gerenciador de segredos do Colab. Microdados do SINAN, snapshots Parquet e modelos treinados não devem ser versionados.

Este repositório faz parte de um Trabalho de Conclusão de Curso.
