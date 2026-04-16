# 🔌 Backend

API REST para o sistema de vigilância WBE-IoT.

## Tecnologias

- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Banco de Dados**: PostgreSQL
- **Message Broker**: MQTT (Mosquitto)
- **ORM**: SQLAlchemy

## 🏗️ Estrutura (A Implementar)

```
/backend
├── main.py              # Aplicação principal
├── requirements.txt     # Dependências
├── config.py            # Configurações
├── models/              # Modelos de dados
├── routes/              # Endpoints da API
├── services/            # Lógica de negócio
└── mqtt_client.py       # Cliente MQTT
```

## 🚀 Como Começar

### 1. Instalar dependências
```bash
cd backend
pip install -r ../requirements.txt
```

### 2. Configurar banco de dados
```bash
# Certifique-se que PostgreSQL está rodando (Docker)
docker-compose up -d postgres
```

### 3. Executar a API
```bash
python main.py
```

A API estará disponível em: `http://localhost:8000`

### 4. Documentação Interativa
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📡 Endpoints (A Implementar)

- `GET /api/wbe/latest` - Último índice WBE
- `GET /api/wbe/history` - Histórico de WBE
- `GET /api/health` - Health check da API
- `POST /api/data/upload` - Fazer upload de dados

## 🔄 Integração com MQTT

O backend:
1. Se conecta ao broker MQTT
2. Faz subscribe ao tópico `iot/wbe/index`
3. Recebe dados do IoT Simulator
4. Processa e armazena no PostgreSQL

## 📝 Variáveis de Ambiente

Ver `.env.example` na raiz do projeto.
