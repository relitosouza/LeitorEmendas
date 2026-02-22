# Supabase Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the manual file-upload flow with a Supabase-backed database so users can search directly on mobile without uploading files.

**Architecture:** Admin runs local Python scripts to ingest XLSX/PDF (deputados) and JSON API (vereadores) into a single Supabase `emendas` table. The Flask app on Vercel drops all upload/file logic and queries Supabase directly. The frontend drops all upload UI and shows a clean search-only experience.

**Tech Stack:** Python 3, Flask, Pandas, supabase-py 2.x, python-dotenv, pytest (tests), Vercel (deploy)

---

## Pre-requisites (manual steps before coding)

1. Create a free Supabase project at https://supabase.com
2. Copy **Project URL** and **service_role key** (Settings → API)
3. Note the public API URL for Vereadores SP JSON (you have this)

---

### Task 1: Update Dependencies & Environment Files

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-scripts.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Modify: `.gitignore`

**Step 1: Rewrite `requirements.txt`** (only what Vercel Flask needs — no pdfplumber)

```
flask==3.1.0
pandas==2.2.3
numpy==2.2.3
openpyxl==3.1.5
supabase==2.10.0
python-dotenv==1.0.1
```

**Step 2: Create `requirements-scripts.txt`** (for local ingestion scripts)

```
pandas==2.2.3
numpy==2.2.3
openpyxl==3.1.5
pdfplumber==0.11.9
supabase==2.10.0
python-dotenv==1.0.1
requests==2.32.3
```

**Step 3: Create `requirements-dev.txt`** (for running tests locally)

```
pytest==8.3.4
pytest-mock==3.14.0
-r requirements-scripts.txt
```

**Step 4: Create `.env.example`**

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key-here
VEREADORES_API_URL=https://example.com/api/vereadores
```

**Step 5: Add `.env` to `.gitignore`**

Open `.gitignore` (create it if it doesn't exist) and add:

```
.env
__pycache__/
*.pyc
venv/
data/
```

**Step 6: Install dev dependencies**

```bash
pip install -r requirements-dev.txt
```

Expected: packages install without errors.

**Step 7: Copy `.env.example` to `.env` and fill in your real values**

```bash
cp .env.example .env
# Then edit .env with your real Supabase URL, key, and vereadores API URL
```

**Step 8: Commit**

```bash
git add requirements.txt requirements-scripts.txt requirements-dev.txt .env.example .gitignore
git commit -m "chore: add supabase deps, split requirements, add env example"
```

---

### Task 2: Create Supabase Table

**Files:**
- Create: `scripts/sql/create_table.sql` (for reference/documentation)

**Step 1: Run this SQL in Supabase Dashboard → SQL Editor**

```sql
create table emendas (
  id           bigint generated always as identity primary key,
  tipo         text not null,
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

**Step 2: Save SQL to file for documentation**

```bash
mkdir -p scripts/sql
```

Create `scripts/sql/create_table.sql` with the SQL above.

**Step 3: Commit**

```bash
git add scripts/sql/create_table.sql
git commit -m "docs: add Supabase table creation SQL"
```

---

### Task 3: Create `scripts/db_utils.py` (shared normalization + client)

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/db_utils.py`
- Create: `tests/__init__.py`
- Create: `tests/test_db_utils.py`

**Step 1: Write the failing tests first**

Create `tests/__init__.py` (empty file).

Create `tests/test_db_utils.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.db_utils import parse_moeda, normalize_deputado_row, normalize_vereador_row


def test_parse_moeda_string_br():
    assert parse_moeda("1.234,56") == 1234.56


def test_parse_moeda_string_r():
    assert parse_moeda("R$ 500,00") == 500.00


def test_parse_moeda_float():
    assert parse_moeda(1000.0) == 1000.0


def test_parse_moeda_nan():
    import math
    assert parse_moeda(float('nan')) == 0.0


def test_normalize_deputado_row_basic():
    row = {
        'nome': 'João Silva',
        'partido': 'PT',
        'ano': 2024,
        'municipio': 'São Paulo',
        'funcao': 'Saúde',
        'orgao': 'Hospital X',
        'objeto': 'Equipamentos',
        'codigo': 'EMD-001',
        'status': 'Pago',
        'data': '2024-03-15',
        'valor_num': 50000.0,
        'pago_flag': True,
    }
    result = normalize_deputado_row(row, ano=2024)
    assert result['tipo'] == 'deputado'
    assert result['nome'] == 'João Silva'
    assert result['pago'] == True
    assert result['valor'] == 50000.0
    assert result['ano'] == 2024


def test_normalize_deputado_row_missing_fields():
    row = {'nome': 'Maria', 'valor_num': 0.0, 'pago_flag': False}
    result = normalize_deputado_row(row, ano=2023)
    assert result['tipo'] == 'deputado'
    assert result['partido'] is None
    assert result['municipio'] is None


def test_normalize_vereador_row_basic():
    row = {
        'nome_vereador': 'Carlos Souza',
        'partido': 'PSDB',
        'ano': 2024,
        'municipio': 'São Paulo',
        'valor': 30000.0,
        'status': 'pago',
        'objeto': 'Obras',
        'codigo': 'VER-001',
    }
    result = normalize_vereador_row(row, ano=2024)
    assert result['tipo'] == 'vereador'
    assert result['nome'] == 'Carlos Souza'
    assert result['pago'] == True
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db_utils.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.db_utils'`

**Step 3: Create `scripts/__init__.py`** (empty file)

**Step 4: Create `scripts/db_utils.py`**

```python
import os
import math
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def parse_moeda(val) -> float:
    """Convert Brazilian currency string or number to float."""
    if val is None:
        return 0.0
    if isinstance(val, float):
        return 0.0 if math.isnan(val) else val
    if isinstance(val, (int,)):
        return float(val)
    val_str = str(val).replace('R$', '').strip()
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0


def _safe(val, default=None):
    """Return None for NaN/NaT, otherwise the value."""
    if val is None:
        return default
    if isinstance(val, float) and math.isnan(val):
        return default
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


def normalize_deputado_row(row: dict, ano: int) -> dict:
    """Convert a processed DataFrame row (dict) to an emendas table row."""
    data_val = _safe(row.get('data'))
    if data_val and data_val != '-':
        # Attempt to parse date; if unparseable, store None
        try:
            data_val = str(pd.to_datetime(data_val).date())
        except Exception:
            data_val = None
    else:
        data_val = None

    return {
        'tipo': 'deputado',
        'nome': str(row.get('nome', '')).strip(),
        'partido': _safe(row.get('partido')),
        'ano': ano,
        'municipio': _safe(row.get('municipio')),
        'funcao': _safe(row.get('funcao')),
        'beneficiario': _safe(row.get('orgao')),
        'objeto': _safe(row.get('objeto')),
        'codigo': _safe(row.get('codigo')),
        'status': _safe(row.get('status')),
        'data_pago': data_val,
        'valor': float(row.get('valor_num', 0.0) or 0.0),
        'pago': bool(row.get('pago_flag', False)),
    }


def normalize_vereador_row(row: dict, ano: int) -> dict:
    """
    Convert a vereador JSON API row to an emendas table row.
    Field mapping: adjust 'nome_vereador' key to match the real API field name.
    """
    nome = (
        row.get('nome_vereador')
        or row.get('nome_parlamentar')
        or row.get('nome')
        or ''
    )
    status = str(row.get('status', '')).lower()
    pago = 'pago' in status

    data_val = _safe(row.get('data_pagamento') or row.get('data_pago'))
    if data_val:
        try:
            data_val = str(pd.to_datetime(data_val).date())
        except Exception:
            data_val = None

    return {
        'tipo': 'vereador',
        'nome': str(nome).strip(),
        'partido': _safe(row.get('partido')),
        'ano': ano,
        'municipio': _safe(row.get('municipio')),
        'funcao': _safe(row.get('funcao') or row.get('funcao_governo')),
        'beneficiario': _safe(row.get('beneficiario') or row.get('orgao')),
        'objeto': _safe(row.get('objeto') or row.get('descricao')),
        'codigo': _safe(row.get('codigo') or row.get('id')),
        'status': _safe(row.get('status')),
        'data_pago': data_val,
        'valor': parse_moeda(row.get('valor') or row.get('valor_decisao', 0)),
        'pago': pago,
    }
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_db_utils.py -v
```

Expected: all 8 tests PASS.

**Step 6: Commit**

```bash
git add scripts/__init__.py scripts/db_utils.py tests/__init__.py tests/test_db_utils.py
git commit -m "feat: add db_utils with normalization functions and tests"
```

---

### Task 4: Create `scripts/ingest_deputados.py`

**Files:**
- Create: `scripts/ingest_deputados.py`
- Create: `tests/test_ingest_deputados.py`

**Step 1: Write the failing tests**

Create `tests/test_ingest_deputados.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from scripts.ingest_deputados import load_file, build_rows


def test_load_xlsx_returns_dataframe(tmp_path):
    # Create a minimal XLSX with expected columns
    df = pd.DataFrame({
        'PARLAMENTAR': ['João Silva'],
        'PARTIDO': ['PT'],
        'ANO': [2024],
        'MUNICÍPIO': ['São Paulo'],
        'VALOR DECISÃO': ['R$ 10.000,00'],
        'ESTÁGIO': ['Pago'],
    })
    xlsx_path = tmp_path / "2024.xlsx"
    df.to_excel(xlsx_path, index=False)

    result = load_file(str(xlsx_path))
    assert isinstance(result, pd.DataFrame)
    assert 'nome' in result.columns
    assert 'valor_num' in result.columns


def test_build_rows_returns_list_of_dicts():
    df = pd.DataFrame({
        'nome': ['João Silva'],
        'partido': ['PT'],
        'municipio': ['São Paulo'],
        'valor_num': [10000.0],
        'pago_flag': [True],
        'status': ['Pago'],
    })
    rows = build_rows(df, ano=2024)
    assert len(rows) == 1
    assert rows[0]['tipo'] == 'deputado'
    assert rows[0]['nome'] == 'João Silva'
    assert rows[0]['ano'] == 2024


def test_build_rows_skips_empty_names():
    df = pd.DataFrame({
        'nome': ['', '  ', 'Maria'],
        'valor_num': [0.0, 0.0, 5000.0],
        'pago_flag': [False, False, False],
    })
    rows = build_rows(df, ano=2024)
    assert len(rows) == 1
    assert rows[0]['nome'] == 'Maria'
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ingest_deputados.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.ingest_deputados'`

**Step 3: Create `scripts/ingest_deputados.py`**

```python
"""
Ingestion script for Deputados Estaduais SP (XLSX 2023+ and PDF pre-2022).

Usage:
    python scripts/ingest_deputados.py path/to/2024.xlsx
    python scripts/ingest_deputados.py path/to/2021.pdf
"""
import sys
import os
import io
import argparse

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pdfplumber

from scripts.db_utils import get_supabase_client, normalize_deputado_row, parse_moeda


# ── Column normalizer (from original app.py) ────────────────────────────────

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and parse values from XLSX/CSV."""
    colunas_ignoradas = set()
    columns_list = list(df.columns)
    for col in columns_list:
        lower_col = str(col).lower().strip()
        if any(k in lower_col for k in ['órgão processador', 'orgao processador',
                                         'primeira fase', 'substituída', 'substituida',
                                         'natureza', 'valor remanejado']):
            colunas_ignoradas.add(col)

    col_mapper = {}
    mapped_values = set()

    for col in columns_list:
        if col in colunas_ignoradas:
            continue
        lower_col = str(col).lower().strip()
        if 'nome' not in mapped_values and any(k in lower_col for k in ['parlamentar', 'deputad', 'autor']):
            col_mapper[col] = 'nome'; mapped_values.add('nome')
        elif 'valor' not in mapped_values and ('valor decisão' in lower_col or 'valor decisao' in lower_col):
            col_mapper[col] = 'valor'; mapped_values.add('valor')
        elif 'municipio' not in mapped_values and ('município' in lower_col or 'municipio' in lower_col):
            col_mapper[col] = 'municipio'; mapped_values.add('municipio')
        elif 'funcao' not in mapped_values and ('função de governo' in lower_col or 'função' in lower_col or 'funcao' in lower_col):
            col_mapper[col] = 'funcao'; mapped_values.add('funcao')
        elif 'data' not in mapped_values and 'data pagamento' in lower_col:
            col_mapper[col] = 'data'; mapped_values.add('data')
        elif 'orgao' not in mapped_values and ('beneficiário' in lower_col or 'beneficiario' in lower_col):
            col_mapper[col] = 'orgao'; mapped_values.add('orgao')
        elif 'status' not in mapped_values and ('estágio' in lower_col or 'estagio' in lower_col):
            col_mapper[col] = 'status'; mapped_values.add('status')
        elif 'partido' not in mapped_values and 'partido' in lower_col:
            col_mapper[col] = 'partido'; mapped_values.add('partido')
        elif 'codigo' not in mapped_values and ('código' in lower_col or 'codigo' in lower_col):
            col_mapper[col] = 'codigo'; mapped_values.add('codigo')
        elif 'objeto' not in mapped_values and 'objeto' in lower_col:
            col_mapper[col] = 'objeto'; mapped_values.add('objeto')

    for col in columns_list:
        if col in col_mapper or col in colunas_ignoradas:
            continue
        lower_col = str(col).lower().strip()
        if 'nome' not in mapped_values and 'nome' in lower_col and 'município' not in lower_col:
            col_mapper[col] = 'nome'; mapped_values.add('nome')
        elif 'valor' not in mapped_values and 'valor' in lower_col:
            col_mapper[col] = 'valor'; mapped_values.add('valor')
        elif 'orgao' not in mapped_values and ('órgão' in lower_col or 'orgao' in lower_col):
            col_mapper[col] = 'orgao'; mapped_values.add('orgao')
        elif 'data' not in mapped_values and 'data' in lower_col:
            col_mapper[col] = 'data'; mapped_values.add('data')

    df = df.rename(columns=col_mapper)
    if 'nome' in df.columns:
        df['nome'] = df['nome'].astype(str).str.strip()
    if 'valor' in df.columns:
        df['valor_num'] = df['valor'].apply(parse_moeda)
    if 'status' in df.columns:
        df['pago_flag'] = df['status'].astype(str).str.lower().str.contains('pago')
    else:
        df['pago_flag'] = False
    return df


def extract_pdf_dataframe(file_path: str) -> pd.DataFrame:
    """Extract table from PDF (pre-2022 format)."""
    all_rows = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                cleaned = [row for row in table if row and any(c and c.strip() for c in row)]
                all_rows.extend(cleaned)

    if not all_rows:
        raise ValueError("No table found in PDF.")

    header_idx = 0
    for i, row in enumerate(all_rows[:20]):
        row_str = ' '.join(str(c).upper() for c in row if c)
        if 'PARLAMENTAR' in row_str and any(k in row_str for k in ['VALOR', 'MUNICÍPIO', 'BENEFICI']):
            header_idx = i
            break

    header = [str(h).replace('\n', ' ').strip().upper() if h else f"COL_{i}"
              for i, h in enumerate(all_rows[header_idx])]
    data = [r for r in all_rows[header_idx + 1:]
            if not any(k in ' '.join(str(c).upper() for c in r if c)
                       for k in ['PARLAMENTAR', 'EMENDAS IMPOSITIVAS'])]

    df = pd.DataFrame(data, columns=header)
    # Rename PDF columns
    pdf_mapper = {}
    for col in df.columns:
        if 'PARLAMENTAR' in col: pdf_mapper[col] = 'nome'
        elif 'BENEFICIÁRIO' in col or 'BENEFICIARIO' in col: pdf_mapper[col] = 'orgao'
        elif 'MUNICÍPIO' in col or 'MUNICIPIO' in col: pdf_mapper[col] = 'municipio'
        elif 'OBJETO' in col: pdf_mapper[col] = 'objeto'
        elif 'VALOR' in col: pdf_mapper[col] = 'valor'
        elif 'STATUS' in col: pdf_mapper[col] = 'status'
    df = df.rename(columns=pdf_mapper)
    for col in ['partido', 'codigo', 'data', 'funcao']:
        if col not in df.columns:
            df[col] = None
    if 'nome' in df.columns:
        df['nome'] = df['nome'].astype(str).str.strip()
    if 'valor' in df.columns:
        df['valor_num'] = df['valor'].apply(parse_moeda)
    if 'status' in df.columns:
        df['pago_flag'] = df['status'].astype(str).str.lower().str.contains('pago')
    else:
        df['pago_flag'] = False
    return df


def load_file(file_path: str) -> pd.DataFrame:
    """Load XLSX, XLS, CSV, or PDF and return a normalized DataFrame."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(file_path)
        return process_dataframe(df)
    elif ext == '.csv':
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='latin-1')
        return process_dataframe(df)
    elif ext == '.pdf':
        return extract_pdf_dataframe(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def detect_ano(df: pd.DataFrame, filename: str) -> int:
    """Detect year from DataFrame ANO column or filename."""
    ano_cols = [c for c in df.columns if str(c).upper() == 'ANO']
    if ano_cols:
        try:
            return int(df[ano_cols[0]].mode().iloc[0])
        except Exception:
            pass
    # Fall back to filename (e.g., "2024.xlsx" -> 2024)
    base = os.path.splitext(os.path.basename(filename))[0]
    try:
        return int(base)
    except ValueError:
        raise ValueError(f"Cannot detect year from file '{filename}'. "
                         "Name the file as YYYY.xlsx or ensure an ANO column exists.")


def build_rows(df: pd.DataFrame, ano: int) -> list:
    """Convert DataFrame to list of dicts ready for Supabase insert."""
    rows = []
    for _, row in df.iterrows():
        nome = str(row.get('nome', '')).strip()
        if not nome:
            continue
        rows.append(normalize_deputado_row(row.to_dict(), ano=ano))
    return rows


def ingest(file_path: str, dry_run: bool = False):
    df = load_file(file_path)
    ano = detect_ano(df, file_path)
    rows = build_rows(df, ano)

    print(f"Loaded {len(rows)} rows for ano={ano} from '{file_path}'")

    if dry_run:
        print("[dry-run] Skipping database write.")
        return

    client = get_supabase_client()
    # Delete existing records for this type+year before inserting
    client.table('emendas').delete().eq('tipo', 'deputado').eq('ano', ano).execute()
    print(f"Deleted existing deputado rows for ano={ano}")

    # Insert in batches of 500
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        client.table('emendas').insert(batch).execute()
        print(f"  Inserted batch {i // batch_size + 1} ({len(batch)} rows)")

    print(f"Done. Total inserted: {len(rows)} rows.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest deputados data into Supabase')
    parser.add_argument('file', help='Path to XLSX, XLS, CSV, or PDF file')
    parser.add_argument('--dry-run', action='store_true', help='Parse only, do not write to DB')
    args = parser.parse_args()
    ingest(args.file, dry_run=args.dry_run)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ingest_deputados.py -v
```

Expected: all 3 tests PASS.

**Step 5: Verify the script parses your real file (dry run)**

```bash
python scripts/ingest_deputados.py data/2024.xlsx --dry-run
```

Expected: output like `Loaded 1532 rows for ano=2024 from 'data/2024.xlsx'`

**Step 6: Commit**

```bash
git add scripts/ingest_deputados.py tests/test_ingest_deputados.py
git commit -m "feat: add deputados ingestion script with tests"
```

---

### Task 5: Create `scripts/ingest_vereadores.py`

**Files:**
- Create: `scripts/ingest_vereadores.py`
- Create: `tests/test_ingest_vereadores.py`

> **Note:** The field names in `normalize_vereador_row` in `db_utils.py` use common guesses (`nome_vereador`, `nome_parlamentar`, `nome`). After you run the script for the first time, check if names are coming through correctly and adjust the field mapping in `db_utils.normalize_vereador_row` if needed.

**Step 1: Write the failing tests**

Create `tests/test_ingest_vereadores.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from scripts.ingest_vereadores import fetch_data, build_rows


def test_fetch_data_returns_list(requests_mock):
    import requests
    sample = [{"nome": "Paulo Frange", "partido": "PTB", "valor": 10000}]
    requests_mock.get("https://fake-api.example.com/vereadores", json=sample)

    with patch.dict(os.environ, {"VEREADORES_API_URL": "https://fake-api.example.com/vereadores"}):
        result = fetch_data(ano=2024)
    assert isinstance(result, list)
    assert len(result) == 1


def test_build_rows_returns_correct_tipo():
    raw = [{"nome": "Ana Lima", "partido": "DEM", "valor": 5000.0, "status": "Pago"}]
    rows = build_rows(raw, ano=2024)
    assert rows[0]['tipo'] == 'vereador'
    assert rows[0]['nome'] == 'Ana Lima'


def test_build_rows_skips_empty_names():
    raw = [{"nome": "", "valor": 1000}, {"nome": "Carlos", "valor": 2000}]
    rows = build_rows(raw, ano=2024)
    assert len(rows) == 1
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ingest_vereadores.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Install requests-mock for tests**

```bash
pip install requests-mock
```

Add `requests-mock==1.12.1` to `requirements-dev.txt`.

**Step 4: Create `scripts/ingest_vereadores.py`**

```python
"""
Ingestion script for Vereadores de SP (JSON API).

Usage:
    python scripts/ingest_vereadores.py --ano 2024
    python scripts/ingest_vereadores.py --ano 2024 --dry-run
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
from scripts.db_utils import get_supabase_client, normalize_vereador_row

load_dotenv()


def fetch_data(ano: int) -> list:
    """Fetch vereadores amendment data from the public JSON API."""
    base_url = os.environ["VEREADORES_API_URL"]
    # Adjust query params to match the real API (add ano filter if supported)
    url = f"{base_url}?ano={ano}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    # Some APIs wrap data in a key; unwrap if needed
    if isinstance(data, dict):
        # Common patterns: data['data'], data['results'], data['items']
        for key in ('data', 'results', 'items', 'emendas'):
            if key in data and isinstance(data[key], list):
                return data[key]
    return data if isinstance(data, list) else []


def build_rows(raw: list, ano: int) -> list:
    """Convert raw API rows to list of dicts for Supabase insert."""
    rows = []
    for item in raw:
        nome = (
            str(item.get('nome_vereador') or item.get('nome_parlamentar') or item.get('nome') or '')
        ).strip()
        if not nome:
            continue
        rows.append(normalize_vereador_row(item, ano=ano))
    return rows


def ingest(ano: int, dry_run: bool = False):
    raw = fetch_data(ano)
    rows = build_rows(raw, ano)

    print(f"Fetched {len(rows)} rows for ano={ano}")

    if dry_run:
        if rows:
            print("[dry-run] First row sample:")
            print(rows[0])
        print("[dry-run] Skipping database write.")
        return

    client = get_supabase_client()
    client.table('emendas').delete().eq('tipo', 'vereador').eq('ano', ano).execute()
    print(f"Deleted existing vereador rows for ano={ano}")

    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        client.table('emendas').insert(batch).execute()
        print(f"  Inserted batch {i // batch_size + 1} ({len(batch)} rows)")

    print(f"Done. Total inserted: {len(rows)} rows.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest vereadores data into Supabase')
    parser.add_argument('--ano', type=int, required=True, help='Year to fetch (e.g. 2024)')
    parser.add_argument('--dry-run', action='store_true', help='Fetch only, do not write to DB')
    args = parser.parse_args()
    ingest(args.ano, dry_run=args.dry_run)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_ingest_vereadores.py -v
```

Expected: all 3 tests PASS.

**Step 6: Verify dry-run against real API**

```bash
python scripts/ingest_vereadores.py --ano 2024 --dry-run
```

Expected: fetches rows and prints first row sample. Check that `nome` field is populated correctly. If not, update the field name mapping in `db_utils.normalize_vereador_row`.

**Step 7: Commit**

```bash
git add scripts/ingest_vereadores.py tests/test_ingest_vereadores.py requirements-dev.txt
git commit -m "feat: add vereadores ingestion script with tests"
```

---

### Task 6: Refactor `app.py` — Replace file logic with Supabase queries

**Files:**
- Modify: `app.py`
- Create: `tests/test_app.py`

**Step 1: Write the failing tests**

Create `tests/test_app.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    # Mock Supabase before importing app
    with patch('supabase.create_client') as mock_create:
        mock_sb = MagicMock()
        mock_create.return_value = mock_sb
        os.environ.setdefault('SUPABASE_URL', 'https://fake.supabase.co')
        os.environ.setdefault('SUPABASE_KEY', 'fake-key')
        import app as flask_app
        flask_app.app.config['TESTING'] = True
        with flask_app.app.test_client() as c:
            yield c, mock_sb


def test_search_returns_404_when_no_rows(client):
    c, mock_sb = client
    mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value.data = []
    resp = c.get('/api/parlamentar/nonexistent')
    assert resp.status_code == 404


def test_search_returns_parlamentar_data(client):
    c, mock_sb = client
    fake_rows = [
        {
            'tipo': 'deputado', 'nome': 'João Silva', 'partido': 'PT',
            'ano': 2024, 'municipio': 'São Paulo', 'funcao': 'Saúde',
            'beneficiario': 'Hospital X', 'objeto': 'Equipamentos',
            'codigo': 'EMD-001', 'status': 'Pago', 'data_pago': '2024-03-15',
            'valor': 50000.0, 'pago': True,
        }
    ]
    mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value.data = fake_rows
    resp = c.get('/api/parlamentar/João')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['parlamentar']['nome'] == 'João Silva'
    assert data['parlamentar']['tipo'] == 'deputado'
    assert 'indicadores' in data
    assert 'historico' in data


def test_anos_endpoint_returns_list(client):
    c, mock_sb = client
    mock_sb.table.return_value.select.return_value.execute.return_value.data = [
        {'ano': 2024}, {'ano': 2023}
    ]
    resp = c.get('/api/anos')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'anos' in data
    assert 2024 in data['anos']
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_app.py -v
```

Expected: FAIL (import errors or route not found)

**Step 3: Rewrite `app.py`**

Replace the entire contents of `app.py` with:

```python
from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import numpy as np
import os
import math
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

# ── Supabase client ──────────────────────────────────────────────────────────
_supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


# ── Utilities ────────────────────────────────────────────────────────────────
def safe_val(val, default='-'):
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        f = float(val)
        return default if math.isnan(f) else f
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


# ── CORS ─────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route('/api/anos')
def listar_anos():
    """Return distinct years available in the database."""
    result = _supabase.table('emendas').select('ano').execute()
    anos = sorted({row['ano'] for row in result.data}, reverse=True)
    return jsonify({"anos": anos})


@app.route('/api/parlamentar/<path:query>')
def get_parlamentar_data(query):
    query_lower = query.lower().strip()
    ano = request.args.get('ano')

    q = _supabase.table('emendas').select('*').ilike('nome', f'%{query_lower}%').limit(5000)
    result = q.execute()
    rows = result.data

    if not rows:
        return jsonify({"error": "Nenhum parlamentar encontrado"}), 404

    # Filter by year if requested
    if ano:
        rows = [r for r in rows if str(r.get('ano', '')) == str(ano)]
        if not rows:
            return jsonify({"error": f"Parlamentar sem dados para o ano {ano}"}), 404

    df = pd.DataFrame(rows)
    df['valor_num'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    df['pago_flag'] = df['pago'].astype(bool)

    first = df.iloc[0]
    nome_real = safe_val(first.get('nome'), 'N/A')
    partido_real = safe_val(first.get('partido'), '-')
    tipo_real = safe_val(first.get('tipo'), 'deputado')

    total_val = float(df['valor_num'].sum())
    total_pagos = float(df[df['pago_flag']]['valor_num'].sum())
    pct_pago = (total_pagos / total_val * 100) if total_val > 0 else 0

    # Top municipalities
    top_mun = {}
    if 'municipio' in df.columns:
        mun_grp = df.groupby('municipio')['valor_num'].sum().reset_index()
        for _, row in mun_grp.sort_values('valor_num', ascending=False).iterrows():
            top_mun[str(safe_val(row['municipio'], 'N/A'))] = float(safe_val(row['valor_num'], 0))

    # Priority sector
    setores_prioritarios = []
    top_func = {}
    if 'funcao' in df.columns:
        func_grp = df.groupby('funcao')['valor_num'].sum().reset_index()
        func_sorted = func_grp.sort_values('valor_num', ascending=False)
        if len(func_sorted) > 0:
            top_val = float(safe_val(func_sorted.iloc[0]['valor_num'], 0))
            for _, row in func_sorted.iterrows():
                row_val = float(safe_val(row['valor_num'], 0))
                if row_val == top_val and len(setores_prioritarios) < 2:
                    setores_prioritarios.append({"nome": str(safe_val(row['funcao'], '-')), "valor": row_val})
                else:
                    break
        for _, row in func_sorted.iterrows():
            top_func[str(safe_val(row['funcao'], 'N/A'))] = float(safe_val(row['valor_num'], 0))

    # History table
    historico = []
    for _, row in df.sort_values('valor_num', ascending=False).iterrows():
        historico.append({
            "data": str(safe_val(row.get('data_pago', '-'))),
            "codigo": str(safe_val(row.get('codigo', ''), '')),
            "municipio": str(safe_val(row.get('municipio', ''), '')),
            "objeto": str(safe_val(row.get('objeto', ''), '')),
            "destino": str(safe_val(row.get('beneficiario', ''), '')),
            "status": str(safe_val(row.get('status', ''), '')),
            "is_pago": bool(row.get('pago_flag', False)),
            "valor_raw": float(safe_val(row.get('valor_num', 0), 0)),
        })

    return jsonify({
        "success": True,
        "parlamentar": {
            "nome": nome_real,
            "partido": partido_real,
            "tipo": tipo_real,
        },
        "indicadores": {
            "total_indicado": total_val,
            "count": len(df),
            "execucao_pago": pct_pago,
            "setor_prioritario": setores_prioritarios,
        },
        "top_municipios": top_mun,
        "todas_funcoes": top_func,
        "historico": historico,
    })


@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return render_template_string(f.read())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_app.py -v
```

Expected: all 3 tests PASS.

**Step 5: Run all tests together**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: refactor app.py to use Supabase instead of file uploads"
```

---

### Task 7: Update `index.html` — Remove upload UI, add tipo badge

**Files:**
- Modify: `index.html`

This task involves HTML/JS edits. Make each change carefully — the file is large.

**Step 1: Remove desktop upload controls (lines ~116-130)**

Find this block in the desktop header section and delete it:

```html
<div class="flex items-center gap-2">
    <label for="csvFileInput" ...>...</label>
    <input type="file" id="csvFileInput" .../>
    <label for="pdfFileInput" ...>...</label>
    <input type="file" id="pdfFileInput" .../>
</div>
<div class="h-6 w-px bg-white/30"></div>
<!-- Seletor de Ano -->
<div id="anoSelectorContainer" ...>...</div>
<div class="h-6 w-px bg-white/30" id="anoDivider" ...></div>
```

Keep only the `<form id="searchForm">` block inside the desktop controls div.

**Step 2: Update the empty state message (mobile guide section ~lines 171-213)**

Replace the entire mobile step-guide `<div class="md:hidden ...">` inside emptyState with:

```html
<div class="md:hidden w-full max-w-sm mt-6 space-y-4">
    <div class="flex items-start gap-3 text-left bg-accent/5 border border-accent/20 rounded-lg p-4">
        <span class="flex-shrink-0 w-7 h-7 rounded-full bg-accent text-white text-sm font-bold flex items-center justify-center">1</span>
        <div class="flex-grow">
            <p class="text-sm font-medium text-primary mb-2">Busque o parlamentar</p>
            <form id="searchFormMobile" class="flex items-center gap-2">
                <div class="relative flex-grow">
                    <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted">
                        <span class="material-symbols-outlined text-[18px]">search</span>
                    </span>
                    <input id="searchInputMobile" class="w-full pl-9 pr-3 py-2.5 text-sm border border-primary/15 rounded-lg bg-white text-primary focus:border-accent focus:ring-1 focus:ring-accent/30 placeholder:text-gray-400" placeholder="Nome do Parlamentar..." type="text"/>
                </div>
                <button type="submit" class="bg-accent text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-accent/80 transition-colors active:scale-[0.98]">
                    Buscar
                </button>
            </form>
        </div>
    </div>
</div>
```

Also update the desktop empty state text:

```html
<p class="text-muted max-w-md hidden md:block">Busque pelo nome do parlamentar para visualizar o perfil completo com emendas, municípios beneficiados e indicadores de execução.</p>
```

**Step 3: Add tipo badge to the profile header**

Find `<span id="parlamentarPartido">Partido</span>` in the profile section and add after it:

```html
<span class="ml-2 text-xs font-semibold uppercase tracking-wider bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded-sm" id="parlamentarTipo"></span>
```

**Step 4: Remove mobile bottom sheet upload section**

In the bottom sheet (`#mobileSheet`), remove any file upload labels/inputs. Keep only the search form and year selector.

**Step 5: Update the JavaScript**

In the `<script>` block, make these changes:

**5a. Remove `handleFileUpload` function** (entire function, ~lines 619-663)

**5b. Remove upload event listeners** (lines ~665-675):
```js
// Delete these lines:
fileInput.addEventListener('change', ...);
pdfFileInput.addEventListener('change', ...);
csvFileInputMobile.addEventListener('change', ...);
pdfFileInputMobile.addEventListener('change', ...);
csvFileInputSheet.addEventListener('change', ...);
pdfFileInputSheet.addEventListener('change', ...);
```

**5c. Remove `updateAnoSelector` calls** that reference upload. Keep year selector logic only if syncing between forms.

**5d. Update `doSearch` to remove `anoParam` dependency on upload** — keep optional year filter:

The existing `doSearch` function already handles `?ano=` param — keep it as-is.

**5e. Update `renderDashboard` to show tipo badge**:

Find:
```js
document.getElementById('parlamentarPartido').textContent = data.parlamentar.partido;
```

Add after it:
```js
const tipoEl = document.getElementById('parlamentarTipo');
if (tipoEl) {
    tipoEl.textContent = data.parlamentar.tipo === 'vereador' ? 'Vereador de SP' : 'Deputado Estadual';
}
```

**Step 6: Load available years on page load**

Add this to the script init (before the search form listeners):

```js
// Load available years from API
async function loadAnos() {
    try {
        const resp = await fetch(`${API_BASE}/api/anos`);
        const data = await resp.json();
        if (data.anos && data.anos.length > 0) {
            updateAnoSelector(data.anos, data.anos[0]);
        }
    } catch (e) {
        // Silently ignore - years will be empty
    }
}
loadAnos();
```

**Step 7: Test in browser**

```bash
python app.py
```

Open http://localhost:5000 and verify:
- No upload buttons visible
- Search works and returns parlamentar data
- Tipo badge shows "Deputado Estadual" or "Vereador de SP"
- Year dropdown populates automatically

**Step 8: Commit**

```bash
git add index.html
git commit -m "feat: remove file upload UI, add tipo badge, load years from API"
```

---

### Task 8: Ingest Real Data & Final Verification

**Step 1: Ingest your XLSX data**

```bash
python scripts/ingest_deputados.py data/2024.xlsx
```

Expected: `Done. Total inserted: XXXX rows.`

**Step 2: Ingest additional years (repeat for each file)**

```bash
python scripts/ingest_deputados.py data/2023.xlsx
python scripts/ingest_deputados.py data/2021.pdf
```

**Step 3: Ingest vereadores**

```bash
python scripts/ingest_vereadores.py --ano 2024
```

**Step 4: Run the app and verify search**

```bash
python app.py
```

Search for a known parlamentar in the browser. Verify:
- Profile loads correctly
- Indicadores show correct values
- Tipo badge displays correctly
- Year filter works

**Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete Supabase integration — mobile-ready search without uploads"
```

---

## Summary of Changed Files

| File | Action |
|------|--------|
| `requirements.txt` | Remove pdfplumber, add supabase + python-dotenv |
| `requirements-scripts.txt` | New — local ingestion deps |
| `requirements-dev.txt` | New — pytest + pytest-mock |
| `.env.example` | New — env var template |
| `.gitignore` | Add .env entry |
| `app.py` | Complete rewrite — Supabase queries, remove all upload/file logic |
| `index.html` | Remove upload UI, add tipo badge, load years from API |
| `scripts/db_utils.py` | New — shared normalization functions |
| `scripts/ingest_deputados.py` | New — XLSX/PDF ingestion script |
| `scripts/ingest_vereadores.py` | New — JSON API ingestion script |
| `scripts/sql/create_table.sql` | New — Supabase schema |
| `tests/test_db_utils.py` | New — unit tests |
| `tests/test_ingest_deputados.py` | New — ingestion tests |
| `tests/test_ingest_vereadores.py` | New — ingestion tests |
| `tests/test_app.py` | New — Flask API tests |
