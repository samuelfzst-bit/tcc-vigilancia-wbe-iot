# Executar o dashboard localmente

Este guia permite que os integrantes do TCC executem a versão estável do
dashboard em seus próprios computadores. Execute os comandos a partir da raiz
do repositório.

## Pré-requisitos

- Git;
- Python 3.11 recomendado;
- acesso à internet;
- URI PostgreSQL do papel `tcc_dashboard_app`, fornecida por Samuel ou Larissa
  em canal privado.

Nunca envie a URI em prints, issues, commits ou mensagens públicas. Não use o
usuário administrador `postgres` nem a chave `service_role` para executar o
dashboard.

## 1. Obter o projeto

```bash
git clone https://github.com/samuelfzst-bit/tcc-vigilancia-wbe-iot.git
cd tcc-vigilancia-wbe-iot
```

Se o repositório já estiver no computador:

```bash
git switch main
git pull origin main
```

## 2. Criar o ambiente virtual

### Windows/PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements/frontend.txt
```

Se o PowerShell bloquear a ativação, execute apenas nesta sessão:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements/frontend.txt
```

## 3. Configurar o segredo local

### Windows/PowerShell

```powershell
Copy-Item frontend\.streamlit\secrets.toml.example frontend\.streamlit\secrets.toml
notepad frontend\.streamlit\secrets.toml
```

### Linux/macOS

```bash
cp frontend/.streamlit/secrets.toml.example frontend/.streamlit/secrets.toml
```

Substitua somente o valor local:

```toml
TCC_DB_URL = "postgresql+psycopg://USUARIO:SENHA@HOST:6543/postgres"
```

Use a URI entregue pelos responsáveis pelo banco. Senhas com caracteres
especiais precisam estar corretamente codificadas na URI. Não tente corrigir a
conexão movendo a senha para a parte do endereço do host.

O login compartilhado foi limitado a cinco conexões, opera em modo somente
leitura e acessa apenas `tcc_previsoes_epidemiologicas` e `leituras_sensor`.
Ele não possui acesso às tabelas epidemiológicas brutas nem permissão para
inserir, atualizar ou excluir registros.

O arquivo `frontend/.streamlit/secrets.toml` já está no `.gitignore`. Confirme
antes de qualquer commit:

```bash
git status --short
```

O arquivo de segredo não pode aparecer na saída.

## 4. Iniciar o dashboard

```bash
python -m streamlit run frontend/app.py
```

Acesse `http://localhost:8501`. Valide as três abas:

1. previsão epidemiológica em `t+1` e `t+2`;
2. telemetria do dispositivo IoT;
3. metodologia e limitações.

Para encerrar, volte ao terminal e pressione `Ctrl+C`.

## Erros comuns

### `TCC_DB_URL` ausente

Confirme o nome e o local do arquivo:

```text
frontend/.streamlit/secrets.toml
```

O nome da chave deve ser exatamente `TCC_DB_URL`.

### `password authentication failed`

A senha, o usuário ou a URI estão incorretos. Solicite novamente a URI de
somente leitura; não use a senha do projeto em tentativas improvisadas.

### `failed to resolve host`

Normalmente a URI foi montada incorretamente e parte da senha passou a ser
interpretada como host. Compare a estrutura com o arquivo de exemplo sem
publicar o valor real.

### `streamlit` não reconhecido

Confirme que o ambiente virtual está ativo e execute:

```bash
python -m streamlit run frontend/app.py
```

## Limites da versão atual

- As previsões exibidas são resultados retrospectivos do teste de 2024.
- O módulo IoT mostra leituras físicas armazenadas no Supabase.
- Os sensores não diagnosticam leptospirose e não alimentaram o modelo
  epidemiológico histórico.
- Atualização automática ao vivo e previsão operacional recente permanecem em
  desenvolvimento.
