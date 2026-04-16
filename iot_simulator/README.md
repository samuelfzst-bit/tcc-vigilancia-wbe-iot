# 🤖 IoT Simulator

Gerador de dados sintéticos para simular sensores de WBE-IoT.

## Arquivos

### `mqtt_publisher.py`
Script principal que:
- Gera dados sintéticos de WBE Index
- Publica em tópicos MQTT
- Simula 3 estações de ETE (Estação de Tratamento de Esgoto)

**Dados gerados:**
- `wbe_index`: Índice WBE (0-100)
- `temperatura`: Temperatura do efluente
- `ph`: pH da amostra
- `condutividade`: Condutividade elétrica

## 🚀 Como Executar

### 1. Instalar dependências
```bash
pip install paho-mqtt
```

### 2. Garantir que MQTT Broker está rodando
```bash
docker-compose up -d
```

### 3. Executar o simulador
```bash
python mqtt_publisher.py
```

Você verá mensagens como:
```
✓ Conectado ao MQTT Broker com sucesso!
✓ Enviado: Estação_ETE_1 - WBE Index: 45.32
✓ Enviado: Estação_ETE_2 - WBE Index: 52.18
✓ Enviado: Estação_ETE_3 - WBE Index: 48.97
```

## 📡 Tópicos MQTT

- **Topic**: `iot/wbe/index`
- **QoS**: 0 (Fire and Forget)
- **Payload**: JSON com dados do sensor

Exemplo:
```json
{
  "timestamp": "2024-04-15T10:30:45.123456",
  "location": "Estação_ETE_1",
  "wbe_index": 45.32,
  "temperature": 25.5,
  "ph": 7.2,
  "conductivity": 1250.0
}
```

## 🔧 Configuração

Edite as constantes no topo do script:
```python
MQTT_BROKER = "localhost"  # Endereço do broker
MQTT_PORT = 1883           # Porta MQTT
MQTT_TOPIC = "iot/wbe/index"
PUBLISH_INTERVAL = 5       # Intervalo em segundos
```

## 🛑 Parar o Simulador

Pressione `Ctrl+C` no terminal.
