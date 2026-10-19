-- Acesso compartilhado de somente leitura para o dashboard local.
-- A senha do login e configurada fora do Git depois desta preparacao.

do $$
begin
  if not exists (
    select 1 from pg_roles where rolname = 'tcc_dashboard_reader'
  ) then
    create role tcc_dashboard_reader
      nologin
      nosuperuser
      nocreatedb
      nocreaterole
      noreplication
      nobypassrls;
  end if;

  if not exists (
    select 1 from pg_roles where rolname = 'tcc_dashboard_app'
  ) then
    create role tcc_dashboard_app
      login
      password null
      connection limit 5
      nosuperuser
      nocreatedb
      nocreaterole
      noreplication
      nobypassrls;
  end if;
end
$$;

alter role tcc_dashboard_app connection limit 5;
alter role tcc_dashboard_app set default_transaction_read_only = on;
alter role tcc_dashboard_app set statement_timeout = '15s';
alter role tcc_dashboard_app set idle_in_transaction_session_timeout = '30s';
alter role tcc_dashboard_app set search_path = public, pg_catalog;

grant tcc_dashboard_reader to tcc_dashboard_app;
grant connect on database postgres to tcc_dashboard_reader;
grant usage on schema public to tcc_dashboard_reader;

revoke all privileges on all tables in schema public
from tcc_dashboard_reader;

grant select on table
  public.tcc_previsoes_epidemiologicas,
  public.leituras_sensor
to tcc_dashboard_reader;

drop policy if exists dashboard_reader_select
on public.tcc_previsoes_epidemiologicas;

create policy dashboard_reader_select
on public.tcc_previsoes_epidemiologicas
for select
to tcc_dashboard_reader
using (true);

drop policy if exists dashboard_reader_select
on public.leituras_sensor;

create policy dashboard_reader_select
on public.leituras_sensor
for select
to tcc_dashboard_reader
using (true);

-- A funcao administrativa nao deve ser chamavel pela Data API nem pelo leitor.
revoke execute on function public.rls_auto_enable() from public;
revoke execute on function public.rls_auto_enable() from anon;
revoke execute on function public.rls_auto_enable() from authenticated;
