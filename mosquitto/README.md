# 🐛 Mosquitto - MQTT Broker

Configuração do Eclipse Mosquitto para o sistema WBE-IoT.

## 📁 Estrutura

```
mosquitto/
├── config/
│   └── mosquitto.conf    # Arquivo de configuração
├── data/                 # Armazena dados persistentes
└── log/                  # Arquivo de logs
```

## 🔧 Configuração

O arquivo `mosquitto.conf` define:

- **Listener MQTT**: Porta 1883 (protocolo padrão)
- **Listener WebSocket**: Porta 9001 (para frontend em browser)
- **Persistência**: Dados salvos em `/mosquitto/data`
- **Logging**: Logs em `/mosquitto/log/mosquitto.log`

## 🚀 Iniciar com Docker

```bash
# Subir o container Mosquitto
docker-compose up -d mosquitto

# Verificar logs
docker-compose logs -f mosquitto

# Parar
docker-compose stop mosquitto
```

## 📡 Testar Conexão

### Via terminal (linux/mac)
```bash
# Subscribe a um tópico
mosquitto_sub -h localhost -p 1883 -t "iot/wbe/index"

# Em outro terminal, publicar
mosquitto_pub -h localhost -p 1883 -t "iot/wbe/index" -m "test"
```

### Via Python
```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    print(f"Tópico: {msg.topic}")
    print(f"Payload: {msg.payload.decode()}")

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("iot/wbe/index")
client.loop_forever()
```

## 🔐 Segurança (Futuro)

Para ambiente de produção, adicionar:
- Autenticação (usuário/senha)
- TLS/SSL
- ACL (Access Control List)

## 📊 Monitoramento

Os logs estão disponíveis em:
```bash
docker-compose exec mosquitto cat /mosquitto/log/mosquitto.log
```

Ou via volumes locais:
```bash
cat mosquitto/log/mosquitto.log
```

## 🐛 Troubleshooting

### Porta já em uso
```bash
# Encontrar processo
lsof -i :1883

# Mudar porta em docker-compose.yml
mosquitto:
  ports:
    - "1884:1883"  # Use 1884 em vez de 1883
```

### Permissões de arquivo
```bash
# Se houver erro de permissão
chmod 755 mosquitto/data
chmod 755 mosquitto/log
```

### Resetar dados
```bash
# Limpar dados persistentes
rm -rf mosquitto/data/*
docker-compose restart mosquitto
```
