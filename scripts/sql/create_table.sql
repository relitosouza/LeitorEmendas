-- Run this in Supabase Dashboard → SQL Editor
-- Creates the emendas table for Lupa Cidadã

create table emendas (
  id           bigint generated always as identity primary key,
  tipo         text not null,        -- 'deputado' | 'vereador'
  nome         text not null,
  partido      text,
  ano          integer not null,
  municipio    text,
  funcao       text,
  beneficiario text,
  objeto       text,
  codigo       text,
  status       text,
  data_pago    date,
  valor        numeric(15,2),
  pago         boolean default false
);

-- Indexes for fast name search and type+year filtering
create index idx_emendas_nome on emendas (lower(nome));
create index idx_emendas_tipo_ano on emendas (tipo, ano);
