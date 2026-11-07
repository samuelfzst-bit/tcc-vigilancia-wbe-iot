# Publicar o dashboard

## Plataforma recomendada

Este repositório entrega uma aplicação Streamlit com sessão ativa e comunicação
por WebSocket. A homologação deve ser publicada no **Streamlit Community Cloud**,
não adaptada para Vercel nesta etapa final. Migrar para Vercel exigiria trocar a
arquitetura da interface, aumentando o risco sem melhorar a entrega acadêmica.

## Configuração de homologação

- Repositório: `samuelfzst-bit/tcc-vigilancia-wbe-iot`
- Branch: `integration/tcc-final`
- Arquivo principal: `frontend/app.py`
- Python: 3.12
- Dependências de publicação: `frontend/requirements.txt` referencia o conjunto
  mínimo do painel em `requirements/frontend.txt`.

Cadastre no gerenciador de segredos da plataforma, nunca no Git:

```toml
TCC_DB_URL = "postgresql+psycopg://USUARIO_LEITURA:SENHA@HOST:6543/postgres?sslmode=require"
```

O usuário deve ser de somente leitura e ter acesso apenas às fontes consumidas
pelo dashboard.

## Checklist antes de divulgar a URL

1. confirmar que a branch publicada é `integration/tcc-final`;
2. verificar que as cinco abas abrem sem exceções;
3. conferir conexão das três fontes na aba de qualidade;
4. comparar o horário da última leitura entre cards, tabela e gráfico;
5. confirmar o rótulo **Reconstruída** nas estimativas que não foram emitidas em
   tempo real;
6. ligar o ESP32 e observar uma nova leitura chegar ao Supabase e ao painel;
7. abrir a URL em janela anônima e em um celular;
8. não divulgar a URI do banco em prints, logs ou gravações.

## Promoção para a entrega

A branch de integração é um ambiente de homologação. Somente depois da validação
do grupo e da gravação de evidências deve ser aberto um pull request para `main`.
O merge na `main` é uma decisão separada e não faz parte desta publicação de
homologação.
