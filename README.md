# Lupa Cidadã

Plataforma web para análise e visualização de emendas parlamentares impositivas do Estado de São Paulo, com dados obtidos do [Portal da Transparência](https://www.transparencia.sp.gov.br/home/emendasparlamentares#gsc.tab=0).

## Funcionalidades

- **Upload de planilhas** — Suporte a arquivos `.csv`, `.xlsx` e `.xls` exportados diretamente do Portal da Transparência
- **Busca por parlamentar** — Pesquisa por nome com exibição de perfil completo
- **Multi-ano** — Carregue dados de vários anos e alterne entre eles
- **Foto automática** — Busca a foto do parlamentar na Wikipedia via API MediaWiki
- **Dashboard com indicadores**:
  - Total indicado em emendas
  - Percentual de execução (pago)
  - Setor prioritário (com detecção de empate)
  - Ranking de municípios beneficiados
  - Histórico completo de emendas com status

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3 + Flask |
| Dados | Pandas + NumPy + OpenPyXL |
| Frontend | HTML + Tailwind CSS (CDN) |
| Fontes | Space Grotesk, IBM Plex Sans, IBM Plex Mono |
| Ícones | Material Symbols (Google) |
| Foto | API MediaWiki (Wikipedia PT) |
| Deploy | Vercel (serverless Python) |

## Colunas suportadas

O sistema reconhece automaticamente as 15 colunas do Portal da Transparência SP:

| Coluna original | Uso no sistema |
|----------------|---------------|
| PARLAMENTAR | Nome do parlamentar |
| PARTIDO | Partido político |
| MUNICÍPIO | Município beneficiado |
| FUNÇÃO DE GOVERNO | Setor/área de atuação |
| BENEFICIÁRIO | Órgão destino |
| ESTÁGIO | Status (pago/não pago) |
| DATA PAGAMENTO | Data da transação |
| VALOR DECISÃO | Valor da emenda |
| CÓDIGO | Código identificador |
| OBJETO | Descrição da emenda |
| ANO | Ano de referência |
| ÓRGÃO PROCESSADOR | *(ignorado)* |
| Primeira Fase Substituídas | *(ignorado)* |
| NATUREZA | *(ignorado)* |
| VALOR REMANEJADO | *(ignorado)* |

## Estrutura do projeto

```
LeitorEmendas/
├── app.py              # Backend Flask (API + rotas)
├── index.html          # Frontend (SPA)
├── requirements.txt    # Dependências Python
├── vercel.json         # Configuração Vercel
├── data/               # Planilhas carregadas (local)
└── README.md
```

## Como rodar localmente

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor
python app.py
```

Acesse `http://localhost:5000` no navegador.

## Deploy no Vercel

O projeto está configurado para deploy automático via GitHub. Cada push na branch `main` gera um novo deploy.

```bash
# Deploy manual (opcional)
vercel --prod
```

> **Nota:** No Vercel, o filesystem é read-only. O app usa `/tmp` para armazenamento temporário de uploads, mas os dados não persistem entre cold starts.

## Licença

MIT
