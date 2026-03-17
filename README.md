# Lupa Cidadã

Plataforma web para análise e visualização de emendas parlamentares impositivas do Estado de São Paulo, com dados obtidos do [Portal da Transparência SP](https://www.transparencia.sp.gov.br/home/emendasparlamentares#gsc.tab=0).

## Visão Geral

A Lupa Cidadã permite que qualquer cidadão consulte como parlamentares estaduais (deputados estaduais, federais e vereadores de SP) destinaram emendas parlamentares, com filtros por ano, município e nome do parlamentar.

Os dados são armazenados no Supabase e servidos por uma API Flask. O frontend é uma SPA em HTML puro com Tailwind CSS.

## Funcionalidades

- **Busca por parlamentar** — Pesquisa com autocomplete por nome, exibindo perfil completo com foto, partido e UF
- **Busca por município** — Consulta quais emendas foram destinadas a cada cidade do Estado de SP
- **Filtro por ano** — Alternância entre anos disponíveis nos dados
- **Dashboard de parlamentar** com:
  - Total indicado em emendas
  - Percentual de execução (pago)
  - Setor prioritário (com detecção de empate)
  - Ranking de municípios beneficiados
  - Histórico completo de emendas com status
- **Dashboard de cidade** com:
  - Total de emendas recebidas
  - Maior benfeitor (parlamentar que mais destinou recursos)
  - Setor prioritário
  - Partidos que mais contribuíram
  - Histórico de emendas por parlamentar
- **Foto automática** — Integração com a API da Câmara dos Deputados e fotos oficiais dos vereadores da Câmara Municipal de SP
- **Tema escuro/claro** — Alternância manual via botão no header

## Páginas

| Rota | Arquivo | Descrição |
|------|---------|-----------|
| `/` | `home.html` | Página inicial com busca unificada |
| `/municipios` | `index.html` | Dashboard de cidade |
| `/parlamentar` | `parlamentar.html` | Dashboard de parlamentar |

## API

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/anos` | Lista os anos disponíveis no banco |
| `GET /api/search_nomes?q=<termo>` | Autocomplete de nomes de parlamentares |
| `GET /api/search_municipios?q=<termo>` | Autocomplete de municípios |
| `GET /api/parlamentar/<nome>?ano=<ano>` | Dados completos de um parlamentar |
| `GET /api/cidade/<municipio>?ano=<ano>` | Dados completos de um município |

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3 + Flask |
| Banco de dados | Supabase (PostgreSQL) |
| Dados | Pandas + NumPy + OpenPyXL |
| Frontend | HTML + Tailwind CSS (CDN) |
| Fontes | Space Grotesk, IBM Plex Sans |
| Ícones | Material Symbols (Google) |
| Fotos | API da Câmara dos Deputados + Câmara Municipal SP |
| Deploy | Vercel (serverless Python) |

## Estrutura do Projeto

```
LeitorEmendas/
├── app.py                   # Backend Flask (API REST + rotas HTML)
├── home.html                # Página inicial
├── index.html               # Dashboard de município
├── parlamentar.html         # Dashboard de parlamentar
├── requirements.txt         # Dependências de produção
├── requirements-scripts.txt # Dependências dos scripts de ingestão
├── requirements-dev.txt     # Dependências de desenvolvimento
├── vercel.json              # Configuração de deploy no Vercel
├── data/                    # Planilhas e PDFs fonte (local)
├── docs/                    # Documentação adicional
├── scripts/                 # Scripts de ingestão de dados no Supabase
│   ├── db_utils.py          # Utilitários de conexão e normalização
│   ├── ingest_deputados.py  # Ingestão de deputados estaduais (XLSX/PDF)
│   ├── ingest_federais_api.py # Ingestão via API federal
│   ├── ingest_vereadores.py # Ingestão de vereadores de SP
│   ├── update_db_tipo.py    # Atualiza tipo dos parlamentares no banco
│   └── sql/                 # Scripts SQL (criação de tabelas)
└── tests/                   # Testes automatizados
```

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz com:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon-publica
```

## Como Rodar Localmente

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env  # edite com suas credenciais do Supabase

# Iniciar servidor
python app.py
```

Acesse `http://localhost:5000` no navegador.

## Ingestão de Dados

Os dados são carregados no Supabase via scripts na pasta `scripts/`. Instale as dependências adicionais e execute conforme o tipo de parlamentar:

```bash
pip install -r requirements-scripts.txt

# Deputados estaduais (XLSX 2023+ ou PDF anos anteriores)
python scripts/ingest_deputados.py data/2024.xlsx

# Vereadores de SP
python scripts/ingest_vereadores.py data/vereadores_2024.xlsx
```

## Deploy no Vercel

O projeto está configurado para deploy automático via GitHub. Cada push na branch `main` gera um novo deploy.

```bash
# Deploy manual (opcional)
vercel --prod
```

> **Nota:** No Vercel, o filesystem é read-only. Os dados são servidos diretamente do Supabase, sem dependência de arquivos locais.

## Fonte dos Dados

- [Portal da Transparência SP — Emendas Parlamentares](https://www.transparencia.sp.gov.br/home/emendasparlamentares#gsc.tab=0)
- [API Dados Abertos — Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html)
- [Câmara Municipal de São Paulo — Vereadores](https://www.saopaulo.sp.leg.br/vereadores/membros/)

## Licença

MIT
