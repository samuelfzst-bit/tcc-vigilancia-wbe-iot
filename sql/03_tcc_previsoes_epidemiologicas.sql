-- Previsoes finais efetivamente consumidas pelo dashboard do TCC.
-- Cada linha referencia o corte temporal que originou as features e a semana
-- epidemiologica observada. Nao armazena decisoes metodologicas.

create table public.tcc_previsoes_epidemiologicas (
    id bigint generated always as identity primary key,
    execucao_id text not null,
    versao_modelo text not null,
    git_commit character(40) not null,
    modelo text not null check (modelo = 'poisson'),
    cenario_geografico text not null
        check (cenario_geografico = 'principal_sem_importados_conhecidos'),
    horizonte smallint not null check (horizonte in (1, 2)),
    inicio_semana_t date not null,
    inicio_semana_alvo date not null,
    observado integer not null check (observado >= 0),
    previsto numeric not null check (previsto >= 0),
    limiar_atencao numeric not null check (limiar_atencao >= 0),
    limiar_alerta numeric not null check (limiar_alerta > limiar_atencao),
    nivel_previsto text not null
        check (nivel_previsto in ('normal', 'atencao', 'alerta')),
    alerta_observado boolean generated always as
        (observado::numeric >= limiar_alerta) stored,
    alerta_previsto boolean generated always as
        (previsto >= limiar_alerta) stored,
    erro numeric generated always as (previsto - observado::numeric) stored,
    erro_absoluto numeric generated always as
        (abs(previsto - observado::numeric)) stored,
    criado_em timestamp with time zone not null default now(),
    constraint uq_tcc_previsao_execucao_horizonte_alvo
        unique (execucao_id, horizonte, inicio_semana_alvo),
    constraint ck_tcc_previsao_distancia_horizonte
        check (
            inicio_semana_alvo = inicio_semana_t + (horizonte * 7)
        ),
    constraint ck_tcc_previsao_nivel_consistente
        check (
            (nivel_previsto = 'normal' and previsto < limiar_atencao)
            or (nivel_previsto = 'atencao'
                and previsto >= limiar_atencao and previsto < limiar_alerta)
            or (nivel_previsto = 'alerta' and previsto >= limiar_alerta)
        ),
    constraint fk_tcc_previsao_corte
        foreign key (horizonte, inicio_semana_t)
        references public.tcc_leptospirose_cortes_temporais
            (horizonte, inicio_semana_t)
        on update restrict on delete restrict,
    constraint fk_tcc_previsao_semana_alvo
        foreign key (cenario_geografico, inicio_semana_alvo)
        references public.tcc_leptospirose_semanal
            (cenario_geografico, inicio_semana)
        on update restrict on delete restrict
);

create index idx_tcc_previsoes_inicio_semana_alvo
    on public.tcc_previsoes_epidemiologicas (inicio_semana_alvo desc);

create index idx_tcc_previsoes_corte_origem
    on public.tcc_previsoes_epidemiologicas
        (horizonte, inicio_semana_t);

create index idx_tcc_previsoes_cenario_semana_alvo
    on public.tcc_previsoes_epidemiologicas
        (cenario_geografico, inicio_semana_alvo);

create index idx_tcc_previsoes_nivel_horizonte
    on public.tcc_previsoes_epidemiologicas
        (nivel_previsto, horizonte, inicio_semana_alvo desc);

comment on table public.tcc_previsoes_epidemiologicas is
    'Previsoes finais do Poisson congelado para o dashboard. Alerta oficial em 4; atencao em 2 e camada operacional exploratoria.';

alter table public.tcc_previsoes_epidemiologicas enable row level security;

revoke all on table public.tcc_previsoes_epidemiologicas
    from public, anon, authenticated;
grant select, insert, update, delete
    on table public.tcc_previsoes_epidemiologicas to service_role;
grant usage, select on sequence public.tcc_previsoes_epidemiologicas_id_seq
    to service_role;

-- Nao ha politica para anon/authenticated. O dashboard consulta a tabela
-- exclusivamente pelo backend, com segredo server-side. A telemetria existente
-- tambem permanece sem leitura publica.
