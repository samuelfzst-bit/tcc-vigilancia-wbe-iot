# 🏗️ ARQUITETURA DO SISTEMA

## 📊 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                     SISTEMA WBE-IoT                             │
│                Vigilância de Doenças em Esgoto                  │
└─────────────────────────────────────────────────────────────────┘

                           ┌─────────────┐
                           │   Sensors   │ (ETEs - Estações)
                           │   (Sínte)   │
                           └──────┬──────┘
                                  │
                    ┌─────────────│──────────────┐
                    │                            │
            ┌───────▼────────┐         ┌────────▼──────┐
            │                │         │                │
        ┌───┴──────────┐     │     ┌───┴──────────┐     │
        │ IoT          │     │     │ MQTT Broker  │     │
        │ Simulator    │─────┼────▶│ (Mosquitto)  │     │
        └──────────────┘     │     └───┬──────────┘     │
                             │         │                │
                    ┌────────┼─────────┼────┐           │
                    │        │         │    │           │
            ┌───────▼───┐ ┌──┴─────┐ ┌┴────▼────┐     │
            │  Backend  │ │Database│ │ Frontend │     │
            │  (FastAPI)│ │(PgSQL) │ │(Streamlit│     │
            └───────────┘ └────────┘ └──────────┘     │
                                                      │
            ┌─────────────────────────────────┐       │
            │    Data Science (Notebook)      │       │
            │ (Limpeza & Processamento)       │◄──────┘
            └─────────────────────────────────┘
```

## 🔄 Fluxo de Dados

```
1. COLETA DE DADOS
   ├─ Dados brutos SINAN (epidemiológicos)
   ├─ Dados brutos INMET (meteorológicos)
   └─ Dados sintéticos do IoT Simulator

2. PROCESSAMENTO
   ├─ Notebook Jupyter
   ├─ Limpeza de dados (valores ausentes, outliers)
   ├─ Normalização e padronização
   ├─ Merge de datasets
   └─ Exporta para /data/processed

3. TRANSMISSÃO
   ├─ IoT Simulator publica no MQTT
   ├─ Tópico: iot/wbe/index
   └─ Via JSON com dados dos sensores

4. ARMAZENAMENTO
   ├─ Backend recebe do MQTT
   ├─ Processa e valida
   └─ Armazena em PostgreSQL

5. VISUALIZAÇÃO
   ├─ Frontend busca dados da API
   ├─ Renderiza dashboards interativos
   └─ Mostra em tempo real
```

## 🔗 Componentes Principais

### 1️⃣ IoT Simulator (`iot_simulator/mqtt_publisher.py`)
- **Função**: Gera dados sintéticos de sensores WBE
- **Tecnologia**: Python + paho-mqtt
- **Frequência**: 5 segundos (configurável)
- **Dados**: WBE Index, temperatura, pH, condutividade
- **Saída**: Publica em MQTT

### 2️⃣ MQTT Broker (`mosquitto/`)
- **Função**: Message broker entre IoT e Backend
- **Tecnologia**: Eclipse Mosquitto
- **Portas**: 1883 (MQTT), 9001 (WebSocket)
- **Persistência**: Sim (dados salvos em disco)
- **Tópicos**: `iot/wbe/index`

### 3️⃣ Backend API (`backend/`)
- **Função**: Recebe dados MQTT, processa e armazena
- **Tecnologia**: FastAPI + PostgreSQL
- **Responsabilidades**:
  - Subscribe ao MQTT
  - Validação de dados
  - Armazenamento em BD
  - Endpoints REST para consultas
- **Endpoints** (planejado):
  - `GET /api/wbe/latest` - Último dados
  - `GET /api/wbe/history` - Histórico
  - `POST /api/data/upload` - Upload manual

### 4️⃣ Banco de Dados (`services/postgres`)
- **Tipo**: PostgreSQL
- **Dados armazenados**:
  - Histórico de WBE Index
  - Dados SINAN processados
  - Dados INMET processados
  - Logs de sensores
- **Cadência**: Atualizado em tempo real pelo Backend

### 5️⃣ Frontend Dashboard (`frontend/`)
- **Função**: Interface visual para monitoramento
- **Tecnologia**: Streamlit + Plotly
- **Visualizações**:
  - Gráficos de série temporal
  - Comparação entre datasets
  - Alertas de anomalias
  - Exportação de relatórios
- **Atualização**: A cada 5 segundos

### 6️⃣ Data Science (`notebooks/`)
- **Função**: Análise e processamento de dados
- **Tecnologia**: Jupyter + Pandas + Scikit-learn
- **Atividades**:
  - Exploração de dados (EDA)
  - Engenharia de features
  - Limpeza e normalização
  - Modelagem preditiva (futuro)

## 🌐 Comunicação Entre Componentes

### Backend ↔ MQTT
```
Backend:
  1. Connect ao Mosquitto (port 1883)
  2. Subscribe("iot/wbe/index")
  3. Quando mensagem chega → processa → Store no BD
  
Frequência: Real-time
Protocolo: MQTT v3.1.1
```

### Backend ↔ Database
```
Backend:
  1. SQLAlchemy ORM
  2. Connection Pool
  3. Queries: INSERT, SELECT, UPDATE
  
Frequência: Conforme dados chegam
Banco: PostgreSQL
```

### Frontend ↔ Backend
```
Frontend (Streamlit):
  1. HTTP GET requests
  2. Endpoints REST
  3. JSON responses
  
Frequência: 5 segundos (refresh)
Protocolo: HTTP/REST
```

### Notebook ↔ Data
```
Notebook:
  1. Read: /data/raw/*.csv
  2. Process
  3. Write: /data/processed/*.csv
  
Frequência: Manual (quando executado)
```

## 🗄️ Estrutura de Dados

### Tabela WBE Index (PostgreSQL)
```sql
CREATE TABLE wbe_index (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    location VARCHAR(100),
    wbe_index FLOAT,
    temperature FLOAT,
    ph FLOAT,
    conductivity FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela SINAN Processada
```sql
CREATE TABLE sinan_processed (
    id SERIAL PRIMARY KEY,
    data DATE,
    localizacao VARCHAR(100),
    casos_notificados INT,
    -- ... outras colunas normalizadas
    created_at TIMESTAMP
);
```

### Tabela INMET Processada
```sql
CREATE TABLE inmet_processed (
    id SERIAL PRIMARY KEY,
    data DATE,
    localizacao VARCHAR(100),
    temperatura FLOAT,
    precipitacao FLOAT,
    umidade FLOAT,
    -- ... outras colunas normalizadas
    created_at TIMESTAMP
);
```

## 🚀 Deployment

Todos os componentes podem ser deployados usando:
- **Docker Compose** (local/dev)
- **Kubernetes** (produção)
- **Cloud Platforms**: AWS, Azure, GCP

Arquivo: `docker-compose.yml`

Serviços:
- mosquitto:1883
- postgres:5432
- pgadmin:5050

## 📊 Performance

| Componente | Frequência | Latência |
|-----------|-----------|----------|
| IoT Simulator | 5s | < 100ms |
| MQTT Broker | Real-time | < 50ms |
| Backend | Real-time | < 200ms |
| Database | Queries | < 500ms |
| Frontend | 5s | < 1s |

## 🔐 Segurança (Futuro)

- [ ] Autenticação MQTT
- [ ] TLS/SSL para API
- [ ] Validação de dados
- [ ] Rate limiting
- [ ] Backup automático do BD

## 📝 Documentação Relacionada

- [QUICKSTART.md](QUICKSTART.md) - Guia rápido
- [README.md](README.md) - Visão geral do projeto
- [data/README.md](data/README.md) - Dados
- [backend/README.md](backend/README.md) - API
- [frontend/README.md](frontend/README.md) - Dashboard
