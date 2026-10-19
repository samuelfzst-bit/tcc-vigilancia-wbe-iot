# 📊 Frontend

Dashboard interativo para visualização dos dados WBE-IoT.

## Tecnologias

- **Framework**: Streamlit (Python)
- **Visualização**: Plotly
- **Dataset**: Pandas

> Streamlit foi escolhido por sua simplicidade e prototipagem rápida. Se preferir React/Vue no futuro, considere migrar.

## Componentes implementados

- série observada versus previsão Poisson em `t+1` e `t+2`;
- níveis normal, atenção e alerta;
- leituras recentes de pH, turbidez, TDS e temperatura;
- separação visual e conceitual entre epidemiologia e IoT;
- página de metodologia e limitações.

## 🚀 Como Executar

O guia completo para os integrantes está em
[`docs/EXECUTAR_DASHBOARD.md`](../docs/EXECUTAR_DASHBOARD.md).

### 1. Instalar dependências

Linux/macOS:

```bash
pip install -r requirements/frontend.txt
cp frontend/.streamlit/secrets.toml.example frontend/.streamlit/secrets.toml
# Edite somente a cópia local e informe TCC_DB_URL.
```

Windows/PowerShell:

```powershell
pip install -r requirements/frontend.txt
Copy-Item frontend\.streamlit\secrets.toml.example frontend\.streamlit\secrets.toml
# Edite somente a cópia local e informe TCC_DB_URL.
```

### 2. Executar o dashboard
```bash
streamlit run frontend/app.py
```

O dashboard será aberto em: `http://localhost:8501`

## Estrutura

```
/frontend
├── app.py              # Aplicação principal
├── data_access.py      # Consultas somente leitura
├── domain.py           # Regras de apresentação
└── .streamlit/
    └── secrets.toml.example
```

## Próximas funcionalidades

- [x] Conexão server-side com Supabase/PostgreSQL
- [x] Previsões finais e telemetria no mesmo dashboard
- [ ] Atualização por Realtime/WebSocket
- [ ] Exportar relatórios em PDF
- [ ] Sistema de alertas
- [ ] Análise preditiva

## 🔧 Configuração

Use o segredo `TCC_DB_URL` no servidor. A URI nunca deve ser exibida na página,
salva no Git ou enviada ao navegador. O banco mantém RLS e não permite leitura
anônima das previsões ou da telemetria.

As credenciais distribuídas à equipe devem ser de somente leitura e limitadas
às tabelas consultadas pelo dashboard. Não use o usuário administrador
`postgres`, a chave `service_role` ou uma senha real em exemplos versionados.
