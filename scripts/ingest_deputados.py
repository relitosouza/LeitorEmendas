"""
Ingestion script for Deputados Estaduais SP (XLSX 2023+ and PDF pre-2022).

Usage:
    python scripts/ingest_deputados.py path/to/2024.xlsx
    python scripts/ingest_deputados.py path/to/2021.pdf
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pdfplumber

from scripts.db_utils import get_supabase_client, normalize_deputado_row, parse_moeda


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and parse values from XLSX/CSV."""
    colunas_ignoradas = set()
    columns_list = list(df.columns)
    for col in columns_list:
        lower_col = str(col).lower().strip()
        if any(k in lower_col for k in ['órgão processador', 'orgao processador',
                                         'primeira fase', 'substituída', 'substituida',
                                         'valor remanejado']):
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
        elif 'natureza' not in mapped_values and 'natureza' in lower_col:
            col_mapper[col] = 'natureza'; mapped_values.add('natureza')

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
    client.table('emendas').delete().eq('tipo', 'deputado').eq('ano', ano).execute()
    print(f"Deleted existing deputado rows for ano={ano}")

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
