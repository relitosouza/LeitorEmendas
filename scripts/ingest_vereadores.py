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
    url = f"{base_url}?ano={ano}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
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
