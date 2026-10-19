# Início rápido

## Modelagem no Google Colab

1. Abra `notebooks/01_extracao_e_auditoria.ipynb` no Colab.
2. Cadastre `TCC_DB_URL` em **Segredos** com uma conexão PostgreSQL de leitura.
3. Instale as dependências indicadas no notebook.
4. Execute todas as células e confirme que o contrato termina sem erros.
5. Salve o snapshot versionado no Drive, fora do Git.

O notebook consulta a view privada `tcc_private.dataset_modelagem`; não use a chave `service_role` no código e não exponha a URL de conexão em outputs.

## Desenvolvimento local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/modeling.txt -r requirements/dev.txt
pytest -q
```

No Windows, ative o ambiente com `.venv\\Scripts\\activate`.

## MQTT

```bash
docker compose up -d
pip install -r requirements/iot.txt
python iot_simulator/mqtt_publisher.py
```

O broker fica em `localhost:1883`. Os valores de conexão podem ser alterados em `.env`, criado a partir de `.env.example`.

## Ordem de trabalho

1. congelar e validar o dataset temporal;
2. rodar baselines;
3. treinar modelos candidatos com validação temporal;
4. calibrar alertas usando apenas validação;
5. abrir o teste de 2024 uma única vez;
6. integrar previsões e telemetria no dashboard.
