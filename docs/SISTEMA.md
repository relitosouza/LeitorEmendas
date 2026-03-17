# Lupa Cidadã — Documentação do Sistema

## Objetivo

A **Lupa Cidadã** é uma plataforma de transparência pública que permite ao cidadão acompanhar como parlamentares do Estado de São Paulo destinam emendas parlamentares impositivas.

O objetivo principal é **democratizar o acesso à informação orçamentária**, tornando dados complexos do Portal da Transparência SP consultáveis de forma simples, visual e intuitiva — sem necessidade de baixar planilhas ou conhecer o sistema governamental.

---

## Problema que Resolve

As emendas parlamentares impositivas são valores que deputados estaduais, deputados federais e vereadores de SP têm o direito de destinar obrigatoriamente ao orçamento público. No entanto:

- Os dados são publicados em planilhas `.xlsx` e `.pdf` de difícil navegação
- Não há ferramenta oficial de busca por parlamentar ou por município
- É impossível comparar parlamentares ou identificar padrões de destinação sem tratar os dados manualmente

A Lupa Cidadã resolve esse problema ingerindo os dados em um banco centralizado e oferecendo uma interface de consulta moderna.

---

## Tipos de Parlamentares Cobertos

| Tipo | Fonte dos dados |
|------|----------------|
| Deputados Estaduais (ALESP) | XLSX/PDF — Portal da Transparência SP |
| Deputados Federais | API da Câmara dos Deputados + Portal da Transparência SP |
| Vereadores de São Paulo | API XML — Câmara Municipal de São Paulo (PMSP) |

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND (SPA)                     │
│  home.html  │  index.html (cidade)  │  parlamentar.html │
└─────────────────────────┬───────────────────────────┘
                          │ HTTP (fetch / JSON)
┌─────────────────────────▼───────────────────────────┐
│               BACKEND — Flask (app.py)               │
│                                                       │
│  /api/anos              lista anos disponíveis        │
│  /api/search_nomes      autocomplete de parlamentares │
│  /api/search_municipios autocomplete de municípios    │
│  /api/parlamentar/<n>   perfil completo               │
│  /api/cidade/<c>        dados de um município         │
└─────────────────────────┬───────────────────────────┘
                          │ supabase-py (REST)
┌─────────────────────────▼───────────────────────────┐
│             BANCO DE DADOS — Supabase                │
│              (PostgreSQL gerenciado)                  │
│                                                       │
│  tabela: emendas                                      │
│   id, tipo, nome, partido, ano, municipio, funcao,    │
│   beneficiario, objeto, codigo, status,               │
│   data_pago, valor, pago                              │
└─────────────────────────────────────────────────────┘
```

### Fluxo de Ingestão de Dados

```
Fontes externas (Portal SP, API PMSP, API Câmara)
        │
        ▼
scripts/ingest_*.py  ←  normalização via db_utils.py
        │
        ▼
    Supabase (tabela emendas)
        │
        ▼
    app.py  →  Frontend
```

---

## Banco de Dados

### Tabela `emendas`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | bigint (PK) | Identificador auto-incremental |
| `tipo` | text | `'deputado'` ou `'vereador'` |
| `nome` | text | Nome do parlamentar |
| `partido` | text | Sigla do partido |
| `ano` | integer | Ano de referência da emenda |
| `municipio` | text | Município beneficiado |
| `funcao` | text | Função de governo (setor: Saúde, Educação, etc.) |
| `beneficiario` | text | Órgão ou entidade destinatária |
| `objeto` | text | Descrição do objeto da emenda |
| `codigo` | text | Código identificador da emenda |
| `status` | text | Status no sistema (ex: Pago, Em processamento) |
| `data_pago` | date | Data do pagamento |
| `valor` | numeric(15,2) | Valor em reais |
| `pago` | boolean | Indica se a emenda foi efetivamente paga |

### Índices

```sql
create index idx_emendas_nome    on emendas (lower(nome));
create index idx_emendas_tipo_ano on emendas (tipo, ano);
```

---

## Scripts de Ingestão

| Script | Fonte | Formato |
|--------|-------|---------|
| `ingest_deputados.py` | Portal Transparência SP | `.xlsx` (2023+) / `.pdf` (até 2022) |
| `ingest_federais_api.py` | API Câmara dos Deputados | REST JSON |
| `ingest_vereadores.py` | API Câmara Municipal SP | XML |
| `update_db_tipo.py` | Supabase | Atualiza campo `tipo` em lote |

### Como executar

```bash
pip install -r requirements-scripts.txt

# Deputados estaduais
python scripts/ingest_deputados.py data/2024.xlsx

# Vereadores (ano específico)
python scripts/ingest_vereadores.py --ano 2024

# Dry-run (sem gravar no banco)
python scripts/ingest_vereadores.py --ano 2024 --dry-run
```

---

## Integração com APIs Externas

### API da Câmara dos Deputados
- **URL:** `https://dadosabertos.camara.leg.br/api/v2/deputados`
- **Uso:** Busca foto, partido e UF de deputados federais
- **Quando é chamada:** Ao renderizar o perfil de um parlamentar do tipo `deputado`

### API da Câmara Municipal de São Paulo (PMSP)
- **Formato:** XML com namespace `http://saeows.saopaulo.sp.leg.br/`
- **Uso:** Ingestão das emendas de vereadores via `ingest_vereadores.py`

### Fotos de Vereadores de SP
- Mapeamento estático em `app.py` com URLs oficiais de `saopaulo.sp.leg.br`
- Cobre os ~55 vereadores da legislatura atual
- Busca por nome com fallback: exata → parcial → sem acento

---

## Frontend

O frontend é composto por três páginas HTML independentes servidas pelo Flask via `render_template_string`.

### Tecnologias
- **Tailwind CSS** (CDN) — estilização utility-first
- **Material Symbols** (Google) — ícones
- **Space Grotesk** + **IBM Plex Sans** — tipografia
- **Fetch API** — comunicação com o backend (sem framework JS)

### Tema escuro/claro
Implementado via classe `dark` no `<html>` com Tailwind `darkMode: "class"`. Preferência salva em `localStorage`.

---

## Deploy

O sistema é hospedado no **Vercel** como função serverless Python.

```json
// vercel.json
{
  "builds": [{ "src": "app.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "app.py" }]
}
```

> No ambiente Vercel o filesystem é **read-only**. Todos os dados são lidos diretamente do Supabase — não há upload de arquivos em produção.

### Variáveis de ambiente necessárias no Vercel

| Variável | Descrição |
|----------|-----------|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | Chave anon/public do Supabase |

---

## Fontes Oficiais dos Dados

- [Portal da Transparência SP — Emendas Parlamentares](https://www.transparencia.sp.gov.br/home/emendasparlamentares)
- [API Dados Abertos — Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html)
- [API Emendas — Câmara Municipal de São Paulo](https://www.saopaulo.sp.leg.br)

---

## Limitações Conhecidas

| Limitação | Descrição |
|-----------|-----------|
| Paginação Supabase | Por padrão o Supabase retorna até 1.000 linhas por query. O endpoint `/api/anos` itera em batches para contornar isso. |
| Fotos de vereadores | O mapeamento é estático e precisa ser atualizado manualmente a cada nova legislatura. |
| Dados federais | Dependem da disponibilidade da API pública da Câmara dos Deputados. |
| Persistência no Vercel | O filesystem serverless é efêmero; dados só persistem no Supabase. |
