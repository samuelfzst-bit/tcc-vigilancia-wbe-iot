# TCC - Vigilância em Saúde via WBE-IoT

Monitoramento de índices de Wastewater-Based Epidemiology (WBE) através de sensores IoT e sistemas em tempo real.

## 📁 Estrutura do Projeto

```
/tcc-vigilancia-wbe-iot
│
├── /data                          # Arquivos de dados
│   ├── /raw                       # CSVs brutos do SINAN e INMET
│   └── /processed                 # Dados após limpeza e normalização
│
├── /notebooks                     # Notebooks de Data Science
│   └── 01_exploracao_dados.ipynb  # Limpeza, normalização e junção dos dados
│
├── /iot_simulator                 # Gerador de dados sintéticos
│   └── mqtt_publisher.py          # Script que envia índice WBE via MQTT/JSON
│
├── /backend                       # API REST (FastAPI ou Flask)
│
├── /frontend                      # Dashboard (React, Vue ou Streamlit)
│
├── .gitignore                     # Ignora arquivos CSV pesados
├── README.md                      # Este arquivo
└── docker-compose.yml             # Broker MQTT + Banco de Dados
```

## 🚀 Como Começar

### Pré-requisitos

- Python 3.8+
- Docker & Docker Compose
- Node.js (se usar React/Vue no frontend)
- Git

### 1. Clonar o Repositório

```bash
git clone <seu-repositorio-url>
cd tcc-vigilancia-wbe-iot
```

### 2. Configurar o Ambiente

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Iniciar os Serviços com Docker

```bash
docker-compose up -d
```

Isso inicia:
- **MQTT Broker** (Mosquitto) em `localhost:1883`
- **PostgreSQL** em `localhost:5432`
- **pgAdmin** em `http://localhost:5050`

### 4. Executar o Simulador IoT

```bash
python iot_simulator/mqtt_publisher.py
```

Isso começará a publicar dados sintéticos de WBE Index no tópico MQTT `iot/wbe/index`.

## 📊 Fluxo de Dados

1. **IoT Simulator** → Gera dados sintéticos de WBE Index
2. **MQTT Broker** → Recebe e distribui mensagens
3. **Backend** → Subscrito ao MQTT, processa e armazena no PostgreSQL
4. **Frontend** → Exibe dados em tempo real no Dashboard

## 🔧 Desenvolvimento

### Backend (FastAPI)

```bash
cd backend
pip install fastapi uvicorn paho-mqtt psycopg2-binary
python main.py
```

### Frontend (Streamlit - Fácil para prototipagem)

```bash
cd frontend
pip install streamlit pandas plotly
streamlit run app.py
```

## 📝 Notebooks

Os notebooks de Data Science estão em `/notebooks`:

- `01_exploracao_dados.ipynb` - Limpeza de dados SINAN e INMET, normalização e junção

## 🐳 Docker

### Parar os serviços

```bash
docker-compose down
```

### Remover volumes (apagar dados do banco)

```bash
docker-compose down -v
```

## ⚠️ Importante: .gitignore

O arquivo `.gitignore` está configurado para **não fazer upload de arquivos CSV** para o repositório. 

Se precisar compartilhar dados, use:
- Google Drive ou OneDrive para arquivos brutos
- Documentação descrevendo como baixar os dados do SINAN e INMET

## 📚 Tecnologias

- **Backend**: Python + FastAPI
- **Banco de Dados**: PostgreSQL
- **Message Broker**: MQTT (Mosquitto)
- **Frontend**: Streamlit (ou React/Vue)
- **Containerização**: Docker & Docker Compose
- **Data Science**: Pandas, NumPy, Scikit-learn

## 👥 Contribuidores

- [Seu Nome] - Desenvolvedor Principal

## 📄 Licença

Este projeto é parte de um TCC (Trabalho de Conclusão de Curso).
