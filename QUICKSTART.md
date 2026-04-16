# 🚀 GUIA DE INÍCIO RÁPIDO

Bem-vindo ao projeto **TCC - Vigilância WBE-IoT**!

## ⚡ Início Rápido (5 minutos)

### 1. Clonar o repositório
```bash
git clone <seu-repositorio>
cd tcc-vigilancia-wbe-iot
```

### 2. Criar ambiente virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Iniciar serviços Docker
```bash
docker-compose up -d
```

Serviços disponíveis:
- **MQTT Broker**: `localhost:1883`
- **PostgreSQL**: `localhost:5432`
- **pgAdmin**: `http://localhost:5050` (admin@wbe.local / admin)

### 5. Rodar o simulador IoT
```bash
python iot_simulator/mqtt_publisher.py
```

### 6. Abrir o Jupyter Notebook
```bash
jupyter notebook notebooks/01_exploracao_dados.ipynb
```

## 📚 Estrutura de Pastas

```
tcc-vigilancia-wbe-iot/
├── data/              # Dados (CSV, raw, processed)
├── notebooks/         # Análises em Jupyter
├── iot_simulator/     # Gerador de dados sintéticos
├── backend/           # API REST (FastAPI)
├── frontend/          # Dashboard (Streamlit)
├── mosquitto/         # Configuração MQTT
├── docker-compose.yml # Serviços containerizados
├── requirements.txt   # Dependências Python
└── README.md          # Este arquivo
```

## 🔄 Fluxo de Trabalho

```
1. Dados Brutos (SINAN, INMET)
         ↓
2. Notebook: Limpeza & Processamento
         ↓
3. Dados Processados
         ↓
4. IoT Simulator → MQTT Broker
         ↓
5. Backend: Recebe e Store
         ↓
6. Frontend: Dashboard
```

## 💡 Próximos Passos

- [ ] Baixar dados SINAN e INMET
- [ ] Executar notebook de exploração
- [ ] Implementar endpoints da API
- [ ] Criar dashboard Streamlit
- [ ] Testar pipeline completo

## 🆘 Troubleshooting

### Docker não funciona
```bash
docker-compose down
docker-compose up -d --build
```

### Porta já em uso
```bash
# Encontrar processo na porta 1883
lsof -i :1883
kill -9 <PID>
```

### Erro no notebook
```bash
# Reiniciar kernel
# Menu: Kernel → Restart & Clear Output
```

## 📖 Documentação Detalhada

Veja os READMEs em cada pasta:
- [data/README.md](data/README.md)
- [notebooks/README.md](notebooks/README.md)
- [iot_simulator/README.md](iot_simulator/README.md)
- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)

## 👥 Colaborando

### Clonar e contribuir
```bash
git clone <repo>
git checkout -b feature/sua-feature
# ... fazer mudanças
git add .
git commit -m "feat: descrição da mudança"
git push origin feature/sua-feature
```

### ⚠️ Importante: .gitignore

Não commitar:
- `*.csv` (dados pesados)
- `__pycache__/`
- `.env` (credenciais)
- `venv/`

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique a documentação em cada pasta
2. Abra uma Issue no GitHub
3. Contacte o desenvolvedor principal

---

**Status**: 🟢 Pronto para uso

**Última atualização**: Abril/2024
