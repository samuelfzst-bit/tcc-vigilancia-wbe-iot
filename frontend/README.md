# 📊 Frontend

Dashboard interativo para visualização dos dados WBE-IoT.

## Tecnologias

- **Framework**: Streamlit (Python)
- **Visualização**: Plotly
- **Dataset**: Pandas

> Streamlit foi escolhido por sua simplicidade e prototipagem rápida. Se preferir React/Vue no futuro, considere migrar.

## 🎨 Componentes (A Implementar)

- 📈 Gráficos de série temporal do WBE Index
- 🗺️ Mapa interativo das estações ETE
- 📊 Comparação entre SINAN, INMET e WBE
- 🔔 Alertas de anomalias
- 📥 Upload e download de dados

## 🚀 Como Executar

### 1. Instalar dependências
```bash
cd frontend
pip install streamlit plotly pandas
```

### 2. Executar o dashboard
```bash
streamlit run app.py
```

O dashboard será aberto em: `http://localhost:8501`

## 📁 Estrutura (A Implementar)

```
/frontend
├── app.py              # Aplicação principal
├── pages/              # Páginas do dashboard
│   ├── home.py
│   ├── analysis.py
│   └── alerts.py
└── components/         # Componentes reutilizáveis
```

## 🎯 Funcionalidades Planejadas

- [ ] Conexão com API Backend
- [ ] Real-time updates via WebSocket
- [ ] Exportar relatórios em PDF
- [ ] Sistema de alertas
- [ ] Análise preditiva

## 🔧 Configuração

Edite `config.py` ou use variáveis de ambiente:
```python
API_URL = "http://localhost:8000"
REFRESH_INTERVAL = 5  # segundos
```
