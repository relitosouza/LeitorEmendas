# Supabase Integration Design — Lupa Cidadã

**Data:** 2026-02-22

---

## Objetivo

Substituir o fluxo de upload manual de arquivos por um banco de dados Supabase pré-carregado, melhorando drasticamente a experiência mobile. Usuários finais apenas consultam dados. O admin popula o banco via scripts locais.

---

## Escopo

- **Deputados Estaduais SP:** XLSX (2023+) e PDF (pré-2022)
- **Vereadores de SP (capital):** JSON via API pública
- **Fora do escopo agora:** vereadores de outros municípios, outros estados

---

## Arquitetura

```
ADMIN (local)
  script_deputados.py   →  lê XLSX/PDF  →  upsert Supabase
  script_vereadores.py  →  busca JSON API  →  upsert Supabase

Vercel (Flask API)
  /api/parlamentar/<query>  →  consulta Supabase  →  response JSON

index.html (SPA)
  busca unificada por nome
  sem upload de arquivo
  badge: "Deputado Estadual" | "Vereador de SP"
```

---

## Schema do Banco de Dados

```sql
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

create index idx_emendas_nome on emendas (lower(nome));
create index idx_emendas_tipo_ano on emendas (tipo, ano);
```

---

## Scripts de Ingestão

### `scripts/ingest_deputados.py`
- Argumento: caminho para arquivo XLSX ou PDF
- Reutiliza `process_dataframe()` / `process_pdf_dataframe()` de `app.py`
- Upsert por `(nome, ano, codigo)` para evitar duplicatas
- Uso: `python scripts/ingest_deputados.py data/2024.xlsx`

### `scripts/ingest_vereadores.py`
- Busca JSON da API pública (URL via `.env`)
- Normaliza para o schema comum
- Upsert por `(nome, ano, codigo)`
- Uso: `python scripts/ingest_vereadores.py --ano 2024`

### `.env` (não versionado)
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=sua-service-role-key
VEREADORES_API_URL=https://...
```

---

## Mudanças no Backend (`app.py`)

**Remove:**
- `/api/upload`
- `/api/anos`
- `/api/ano/<ano>`
- `global_dfs`, `load_saved_files()`
- Dependências: `pdfplumber` (move para scripts)

**Mantém/adapta:**
- `/api/parlamentar/<query>` — consulta Supabase via `supabase-py`
- Retorna campo `tipo` no response

**Nova dependência:** `supabase-py`

---

## Mudanças no Frontend (`index.html`)

**Remove:** tela de upload, seletor de ano manual, botão "carregar arquivo"

**Mantém:** busca por nome, perfil completo, todos os indicadores

**Adiciona:**
- Badge "Deputado Estadual" ou "Vereador de SP" no perfil
- Filtro de ano (dropdown) na tela de resultados

---

## Decisões Tomadas

| Questão | Decisão |
|---------|---------|
| Quem mantém os dados? | Admin via scripts locais |
| Upload para usuários? | Removido completamente |
| Schema | Tabela única `emendas` normalizada |
| Tipos cobertos | Deputados Estaduais SP + Vereadores SP capital |
| Busca | Unificada por nome, retorna ambos os tipos |
