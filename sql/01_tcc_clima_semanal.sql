-- Visão climática semanal usada pelo TCC.
-- Fonte: public.clima_diario, estação A701, período epidemiológico 2010–2024.
-- Regra: cada agregado só existe quando os sete dias da semana têm valor válido.

create materialized view public.tcc_clima_semanal as
with diario as (
    select
        cd.data,
        cd.cod_estacao,
        cd.temperatura_media,
        cd.temperatura_max,
        cd.temperatura_min,
        cd.umidade,
        cd.precipitacao,
        cd.velocidade_vento,
        (public.semana_epidemiologica(cd.data)).ano as ano,
        (public.semana_epidemiologica(cd.data)).semana as semana_epidemiologica
    from public.clima_diario cd
    where cd.cod_estacao = 'A701'
), semanal as (
    select
        cod_estacao,
        ano,
        semana_epidemiologica,
        min(data) as inicio_semana,
        max(data) as fim_semana,
        count(*)::smallint as dias_com_dado,
        count(temperatura_media)::smallint as dias_temperatura_media_validos,
        count(temperatura_max)::smallint as dias_temperatura_max_validos,
        count(temperatura_min)::smallint as dias_temperatura_min_validos,
        count(umidade)::smallint as dias_umidade_validos,
        count(precipitacao)::smallint as dias_precipitacao_validos,
        count(velocidade_vento)::smallint as dias_vento_validos,
        case when count(*) = 7 and count(temperatura_media) = 7 then avg(temperatura_media) end as temperatura_media,
        case when count(*) = 7 and count(temperatura_max) = 7 then max(temperatura_max) end as temperatura_max,
        case when count(*) = 7 and count(temperatura_min) = 7 then min(temperatura_min) end as temperatura_min,
        case when count(*) = 7 and count(umidade) = 7 then avg(umidade) end as umidade_media,
        case when count(*) = 7 and count(precipitacao) = 7 then sum(precipitacao) end as precipitacao_total,
        case when count(*) = 7 and count(velocidade_vento) = 7 then avg(velocidade_vento) end as velocidade_vento_media,
        count(*) = 7 as semana_calendario_completa,
        count(*) = 7
            and count(temperatura_media) = 7
            and count(umidade) = 7
            and count(precipitacao) = 7 as clima_essencial_completo
    from diario
    group by cod_estacao, ano, semana_epidemiologica
)
select *
from semanal
where ano between 2010 and 2024
order by ano, semana_epidemiologica;

create unique index tcc_clima_semanal_ano_semana_uidx
    on public.tcc_clima_semanal (ano, semana_epidemiologica);

comment on materialized view public.tcc_clima_semanal is
    'Série semanal da estação INMET A701 para o TCC. Agregados só são calculados quando os 7 dias da semana possuem valor diário válido para a variável.';

grant select on public.tcc_clima_semanal to anon, authenticated, service_role;
revoke insert, update, delete, truncate, references, trigger
    on public.tcc_clima_semanal from public, anon, authenticated;
