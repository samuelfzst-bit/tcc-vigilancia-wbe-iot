-- Dataset supervisionado temporalmente honesto para o TCC.
-- Unidade: semana epidemiológica de origem x horizonte de previsão.
-- Alvos: contagem final de casos em t+1 ou t+2.
-- Preditores: somente informações disponíveis até data_corte.
-- Nulos são preservados; imputação e escala pertencem ao pipeline de treino.

create or replace view tcc_private.dataset_modelagem
with (security_invoker = true) as
with clima_janelas as (
    select
        c.*,
        lag(c.precipitacao_total, 1) over w as precipitacao_lag_1,
        lag(c.precipitacao_total, 2) over w as precipitacao_lag_2,
        lag(c.precipitacao_total, 3) over w as precipitacao_lag_3,
        lag(c.precipitacao_total, 4) over w as precipitacao_lag_4,
        lag(c.precipitacao_total, 8) over w as precipitacao_lag_8,
        lag(c.precipitacao_total, 12) over w as precipitacao_lag_12,
        lag(c.precipitacao_total, 52) over w as precipitacao_lag_52,
        lag(c.temperatura_media, 1) over w as temperatura_media_lag_1,
        lag(c.temperatura_media, 2) over w as temperatura_media_lag_2,
        lag(c.temperatura_media, 4) over w as temperatura_media_lag_4,
        lag(c.temperatura_media, 8) over w as temperatura_media_lag_8,
        lag(c.temperatura_media, 12) over w as temperatura_media_lag_12,
        lag(c.umidade_media, 1) over w as umidade_media_lag_1,
        lag(c.umidade_media, 2) over w as umidade_media_lag_2,
        lag(c.umidade_media, 4) over w as umidade_media_lag_4,
        lag(c.umidade_media, 8) over w as umidade_media_lag_8,
        lag(c.velocidade_vento_media, 1) over w as vento_medio_lag_1,
        case when count(c.precipitacao_total) over w2 = 2
             then sum(c.precipitacao_total) over w2 end as precipitacao_acum_2s,
        case when count(c.precipitacao_total) over w4 = 4
             then sum(c.precipitacao_total) over w4 end as precipitacao_acum_4s,
        case when count(c.precipitacao_total) over w8 = 8
             then sum(c.precipitacao_total) over w8 end as precipitacao_acum_8s,
        case when count(c.temperatura_media) over w4 = 4
             then avg(c.temperatura_media) over w4 end as temperatura_media_4s,
        case when count(c.temperatura_media) over w8 = 8
             then avg(c.temperatura_media) over w8 end as temperatura_media_8s,
        case when count(c.umidade_media) over w4 = 4
             then avg(c.umidade_media) over w4 end as umidade_media_4s,
        case when count(c.umidade_media) over w8 = 8
             then avg(c.umidade_media) over w8 end as umidade_media_8s,
        count(*) over w4 = 4
          and count(c.precipitacao_total) over w4 = 4
          and count(c.temperatura_media) over w4 = 4
          and count(c.umidade_media) over w4 = 4 as clima_essencial_4s_completo
    from public.tcc_clima_semanal c
    window
        w as (order by c.inicio_semana),
        w2 as (order by c.inicio_semana rows between 1 preceding and current row),
        w4 as (order by c.inicio_semana rows between 3 preceding and current row),
        w8 as (order by c.inicio_semana rows between 7 preceding and current row)
), base as (
    select
        ct.horizonte,
        ct.inicio_semana_t,
        ct.data_corte,
        ct.inicio_semana_alvo,
        ct.ano_alvo,
        (public.semana_epidemiologica(ct.inicio_semana_alvo)).semana::smallint as semana_alvo,
        ct.target_casos,
        ct.split,
        ct.cenario_geografico,
        ct.fonte_disponibilidade,
        ct.casos_conhecidos_lag_0,
        ct.casos_conhecidos_lag_1,
        ct.casos_conhecidos_lag_2,
        ct.casos_conhecidos_lag_3,
        ct.casos_conhecidos_lag_4,
        ct.casos_conhecidos_lag_5,
        ct.casos_conhecidos_lag_8,
        ct.casos_conhecidos_lag_12,
        ct.casos_conhecidos_lag_52,
        ct.media_conhecida_lags_2_5,
        (ct.casos_conhecidos_lag_2 + ct.casos_conhecidos_lag_3
         + ct.casos_conhecidos_lag_4 + ct.casos_conhecidos_lag_5) as soma_conhecida_lags_2_5,
        greatest(ct.casos_conhecidos_lag_2, ct.casos_conhecidos_lag_3,
                 ct.casos_conhecidos_lag_4, ct.casos_conhecidos_lag_5) as max_conhecido_lags_2_5,
        ct.casos_conhecidos_lag_2 - ct.casos_conhecidos_lag_5 as tendencia_conhecida_2_5,
        sin(2 * pi() * (public.semana_epidemiologica(ct.inicio_semana_alvo)).semana / 52.1775) as semana_alvo_sin,
        cos(2 * pi() * (public.semana_epidemiologica(ct.inicio_semana_alvo)).semana / 52.1775) as semana_alvo_cos,
        cj.dias_temperatura_media_validos,
        cj.dias_umidade_validos,
        cj.dias_precipitacao_validos,
        cj.clima_essencial_completo,
        not cj.clima_essencial_completo as flag_clima_t_incompleto,
        cj.temperatura_media as temperatura_media_t,
        cj.temperatura_max as temperatura_max_t,
        cj.temperatura_min as temperatura_min_t,
        cj.umidade_media as umidade_media_t,
        cj.precipitacao_total as precipitacao_t,
        cj.velocidade_vento_media as vento_medio_t,
        cj.precipitacao_lag_1,
        cj.precipitacao_lag_2,
        cj.precipitacao_lag_3,
        cj.precipitacao_lag_4,
        cj.precipitacao_lag_8,
        cj.precipitacao_lag_12,
        cj.precipitacao_lag_52,
        cj.temperatura_media_lag_1,
        cj.temperatura_media_lag_2,
        cj.temperatura_media_lag_4,
        cj.temperatura_media_lag_8,
        cj.temperatura_media_lag_12,
        cj.umidade_media_lag_1,
        cj.umidade_media_lag_2,
        cj.umidade_media_lag_4,
        cj.umidade_media_lag_8,
        cj.vento_medio_lag_1,
        cj.precipitacao_acum_2s,
        cj.precipitacao_acum_4s,
        cj.precipitacao_acum_8s,
        cj.temperatura_media_4s,
        cj.temperatura_media_8s,
        cj.umidade_media_4s,
        cj.umidade_media_8s,
        cj.clima_essencial_4s_completo,
        not cj.clima_essencial_4s_completo as flag_clima_4s_incompleto,
        ct.versao_base as versao_base_epidemiologica,
        'dataset_modelagem_v1_20260927'::text as versao_dataset
    from public.tcc_leptospirose_cortes_temporais ct
    join clima_janelas cj
      on cj.inicio_semana = ct.inicio_semana_t
    where ct.cenario_geografico = 'principal_sem_importados_conhecidos'
)
select * from base;

revoke all on tcc_private.dataset_modelagem from public, anon, authenticated;
grant select on tcc_private.dataset_modelagem to service_role;

comment on view tcc_private.dataset_modelagem is
    'Dataset do TCC para previsão semanal t+1/t+2. Preditores limitados à data_corte; nulos preservados para tratamento exclusivo no pipeline de treino.';
