# 📊 Dados

Diretório para armazenamento de arquivos CSV do projeto.

## Estrutura

### `/raw`
Contém os arquivos CSV brutos, recém-baixados de:
- **SINAN** (Sistema de Informação de Agravos de Notificação)
- **INMET** (Instituto Nacional de Meteorologia)

⚠️ **Importante**: Estes arquivos podem ser grandes e NÃO devem ser colocados no Git (veja `.gitignore`).

### `/processed`
Contém os dados após:
- Limpeza (remoção de valores nulos, outliers)
- Normalização e padronização
- Merge entre datasets

✅ Estes arquivos são gerados pelo notebook `01_exploracao_dados.ipynb`

## 🔄 Fluxo de Dados

1. Baixar dados do SINAN → colocar em `/raw`
2. Baixar dados do INMET → colocar em `/raw`
3. Executar o notebook para processar
4. Arquivos processados aparecem em `/processed`
5. Backend usa dados de `/processed`

## 📥 Como Baixar os Dados

### SINAN
- Acesse: https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/s/sinan
- Baixe os dados em formato CSV
- Coloque em `/raw` com o nome `sinan_data.csv`

### INMET
- Acesse: https://www.inmet.gov.br/
- Requisite dados meteorológicos
- Coloque em `/raw` com o nome `inmet_data.csv`
