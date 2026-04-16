"""
IoT Simulator - MQTT Publisher para WBE Index
Simula um sensor IoT que envia o índice WBE (Wastewater-Based Epidemiology)
via MQTT em formato JSON.
"""

import json
import time
import random
from datetime import datetime
import paho.mqtt.client as mqtt

# Configurações MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/wbe/index"
MQTT_CLIENT_ID = "wbe-iot-publisher"

# Configurações do simulador
SENSOR_LOCATIONS = ["Estação_ETE_1", "Estação_ETE_2", "Estação_ETE_3"]
PUBLISH_INTERVAL = 5  # segundos


def connect_mqtt():
    """Conecta ao broker MQTT"""
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✓ Conectado ao MQTT Broker com sucesso!")
        else:
            print(f"✗ Falha ao conectar. Código: {rc}")

    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print(f"Desconexão inesperada. Código: {rc}")

    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    return client


def generate_wbe_data(location):
    """Gera dados sintéticos do índice WBE"""
    # Simula valores realistas de WBE Index (0-100)
    wbe_index = random.gauss(50, 15)
    wbe_index = max(0, min(100, wbe_index))  # Limita entre 0 e 100

    return {
        "timestamp": datetime.now().isoformat(),
        "location": location,
        "wbe_index": round(wbe_index, 2),
        "temperature": round(random.uniform(20, 35), 2),
        "ph": round(random.uniform(6.5, 8.5), 2),
        "conductivity": round(random.uniform(500, 2000), 2),
    }


def main():
    """Função principal"""
    print("Iniciando IoT Simulator para WBE Index...")

    client = connect_mqtt()
    client.loop_start()

    try:
        time.sleep(2)  # Aguarda conexão

        while True:
            for location in SENSOR_LOCATIONS:
                data = generate_wbe_data(location)
                message = json.dumps(data)

                result = client.publish(MQTT_TOPIC, message)

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f"✓ Enviado: {location} - WBE Index: {data['wbe_index']}")
                else:
                    print(
                        f"✗ Erro ao enviar para {location}: {mqtt.error_string(result.rc)}"
                    )

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n⏹ Parando o simulador...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Desconectado do MQTT Broker.")


if __name__ == "__main__":
    main()
