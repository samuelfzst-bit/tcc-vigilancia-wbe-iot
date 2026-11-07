# Dashboard WBE-IoT

O frontend consulta PostgreSQL com seis abas de análise.
Não utiliza dados fictícios como substituição em caso de erro.

## Iniciar com dois cliques

Abra `Iniciar Dashboard.bat` na raiz do projeto. Ele usa o Python do ambiente
`.venv` ou `venv`, quando existir, ou o Python instalado na máquina. O navegador
abre automaticamente; mantenha a janela aberta durante o uso. Para encerrar,
pressione Ctrl+C nessa janela. Se faltar alguma dependência, o batch mostra
o comando de instalação.

## Configurar

Instale `python -m pip install -r requirements/frontend.txt`.
Preencha `TCC_DB_URL` em `.streamlit/secrets.toml` na raiz do projeto:

```toml
TCC_DB_URL = "postgresql+psycopg://USUARIO:SENHA@HOST:6543/postgres?sslmode=require"
```

Use a URI fornecida pelo responsável pelo banco e um usuário com acesso de leitura.
O arquivo local é ignorado pelo Git. A variável de ambiente TCC_DB_URL tem prioridade;
frontend/.streamlit/secrets.toml também é aceito.

Execute `python -m streamlit run frontend/app.py`.
No canto superior, o estado informa a hora real das consultas concluídas.
O indicador Atualizado às usa o horário de Brasília (UTC−03), apenas na exibição.
Detalhes de falhas e formatos ficam em Qualidade dos dados → Diagnóstico das fontes.
O botão Atualizar agora está em Atualização na lateral; o modo automático já vem ligado.
As fontes consultadas são `public.leituras_sensor`, `public.tcc_previsoes_operacionais_dashboard`
e `public.tcc_previsoes_epidemiologicas` (avaliação histórica).

## Leitura do painel

A Visão geral reúne classificação epidemiológica, evolução do modelo, métricas de
avaliação e conferência das previsões. Abaixo aparecem as últimas leituras dos
quatro sensores. Qualidade dos dados concentra preenchimento, lacunas e registros
com desvios para evitar repetir indicadores em todas as abas.

A aba **Validação histórica**, ao lado da Visão geral, recupera a última execução
publicada na tabela histórica e exibe toda a série disponível, sem limitar às
últimas 12 semanas. A antecedência é fixa em uma semana; não mistura execuções ou horizontes. MAE, RMSE, viés e número de semanas
são calculados somente sobre pares de observado/estimado disponíveis. Observado
zero é válido. Não há porcentagem de acurácia inventada nem promessa de desempenho
futuro. A indisponibilidade dessa fonte é indicada sem substituir o gráfico
operacional por resultados históricos.

A atualização automática vem ligada e consulta novamente a cada 30 segundos
com a sessão aberta. O botão Atualizar agora permite atualizar imediatamente. O timer usa o TTL
compartilhado das leituras e não limpa o cache de todas as sessões.
O filtro padrão dos sensores acompanha as últimas 24 horas relativas ao registro
mais recente disponível, mantendo visível sua idade real. Não substitui a data
do registro pela data atual. Outros recortes e datas personalizadas ficam na lateral.

A consulta de previsões seleciona a execução operacional com geração mais recente
(`gerado_em`), sem misturar execuções. A apresentação usa exclusivamente o horizonte de uma semana dessa execução.
Se ele estiver ausente, informa indisponibilidade, sem recorrer a duas semanas ou a execuções antigas. Não há seletor
de t+1/t+2, e a linha do tempo abre nas últimas 12 semanas dessa série.
As tabelas ordenam por referência ou leitura decrescente; gráficos conservam
ordem cronológica, com os dados recentes à direita. O horizonte permanece no
detalhe de informação para a interpretação da estimativa.

O farol central muda entre verde (normal), amarelo (atenção) e coral (alerta).
Previsões ausentes ou inconsistentes não aparecem como normais. A publicação da execução fica em evidência; a semana de referência e os
detalhes do período avaliado aparecem no ícone de informação, acessível
também pelo teclado. A geração aparece em horário de Brasília; a semana-alvo
continua como data de referência. Resultados reconstruídos têm identificação
própria, sem rótulo de avaliação final de 2024. Consultar em tempo real não
executa treinamento ou inferência: novas previsões devem existir no banco.

O campo `observado_provisorio` é consumido como observado na interface, mantendo
`status_observado`. Quando o status é indisponível ou o valor está ausente, não é
substituído por zero. Sem observados, o gráfico só exibe estimativas/limiares e
não apresenta MAE ou viés. Quando houver observados, a comparação e suas métricas
são rotuladas como provisórias. Não são probabilidades nem métricas do holdout.
Os gráficos usam as interações JavaScript nativas do Plotly para hover, zoom,
legendas e guias de leitura. Datas seguem dd/mm/aaaa HH:mm:ss, em UTC.

O tema escuro é definido em `.streamlit/config.toml`; os componentes visuais
ficam em `presentation.py` e `dashboard.css`. O dashboard só executa SELECT.
Não há criação, atualização ou exclusão de dados nem execução de SQL de migração.

## Serviço do dashboard

`query_service.py` registra separadamente tentativa, conclusão, latência e categoria
de erro de cada leitura. Não registra senha, DSN, dados ou mensagens brutas das
exceções. Uma consulta com falha não recebe horário de sucesso. Fontes vazias,
inacessíveis e incompatíveis têm diagnósticos diferentes. Resultados com horários
inválidos e horizontes fora do contrato também são sinalizados.

`analytics.py` contém os cálculos independentes de Streamlit. A janela usa 12 a 96
registros anteriores, mínimo de 12 valores válidos por indicador e desvio-padrão
amostral. A leitura atual não participa da própria média. Original mantém os
registros; 5/15/30/60 minutos exibem médias, preservando os pontos de desvio originais.
O mínimo de 12 não foi reduzido para dois. Um limite de 20.000 intervalos protege
somente a visualização; solicita recorte menor, sem substituir dados.

O pool permite duas conexões e nenhuma conexão excedente por processo, com espera
máxima de 10 segundos. O timeout de conexão também é 10 segundos; isso não impõe
prazo de execução ao SELECT. A configuração de statement_timeout depende do papel
restrito do banco e não foi alterada. Ao trocar DSN/credenciais no arquivo local,
reinicie o aplicativo para recriar o engine.

A refatoração passou por revisão de fonte, Ruff e 46 testes com fixtures em
contêiner offline, sem segredos ou banco real. Os limites e as pendências de
homologação estão em `docs/REVISAO_DASHBOARD_2026-11-01.md`.


## Celulares e notebooks

O layout usa quebras em 1024, 768 e 359 px: filtros recolhidos inicialmente,
indicadores em duas colunas no celular e uma em telas menores, farol com estimativa
em destaque e limiares abaixo. Abas e tabelas preservam rolagem local. As informações
do farol abrem por toque ou teclado, sem depender de hover. Botões principais têm
área mínima de 44 px; foco visível e preferência por movimento reduzido são preservados.

Os gráficos continuam usando a largura do contêiner. No celular, títulos HTML
quebram em linhas; datas têm menos marcas e as ferramentas ficam visíveis. O zoom
pela roda não intercepta a rolagem e a área de desenho permite gesto vertical.
A prévia de CSS com dados fictícios foi conferida em 320, 360, 390, 768 e 1366 px;
a suíte funcional passou com 55 testes offline. Ainda é necessária homologação
no dispositivo real, incluindo os gráficos interativos e a navegação do Streamlit.

Para acesso por QR code, use a URL do ambiente publicado e acessível aos visitantes.
O iniciador local permanece em localhost; esse endereço não dá acesso pelo celular.
Esta alteração visual não publica o aplicativo nem muda acesso de rede ou banco.
