"""
Ingestion script for Vereadores de SP (XML API).

Usage:
    python scripts/ingest_vereadores.py --ano 2024
    python scripts/ingest_vereadores.py --ano 2024 --dry-run
"""
import sys
import os
import argparse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
from scripts.db_utils import get_supabase_client, normalize_vereador_row

load_dotenv()

# XML namespace used by the PMSP API
_NS = {'ns': 'http://saeows.saopaulo.sp.leg.br/'}


def _parse_xml_rows(content: bytes) -> list:
    """Parse PMSP XML response into a list of dicts."""
    root = ET.fromstring(content)
    rows = []
    for linha in root.findall('ns:Linha', _NS):
        row = {}
        for child in linha:
            tag = child.tag.replace(f'{{{_NS["ns"]}}}', '')
            row[tag] = child.text
        rows.append(row)
    return rows


def fetch_vereadores(ano: int) -> dict:
    """Fetch vereador ID→{nome, partido} mapping for the given year."""
    base_url = os.environ["VEREADORES_API_URL"]
    # The Vereadores endpoint is at the same base, replacing the last path segment
    url = base_url.rsplit('/', 1)[0] + '/Vereadores'
    response = requests.post(
        url,
        data={"exercicio": str(ano)},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    response.raise_for_status()
    rows = _parse_xml_rows(response.content)
    # Map: ID (Numero) → {nome, partido}
    return {
        row['Numero']: {
            'nome': row.get('Nome') or row.get('Apelido') or '',
            'partido': row.get('Partido') or '',
        }
        for row in rows if row.get('Numero')
    }


def fetch_data(ano: int) -> list:
    """Fetch vereadores amendment data from the PMSP XML API."""
    base_url = os.environ["VEREADORES_API_URL"]
    response = requests.post(
        base_url,
        data={"exercicio": str(ano)},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=120,
    )
    response.raise_for_status()
    return _parse_xml_rows(response.content)


def build_rows(raw: list, ano: int, vereadores: dict) -> list:
    """Convert raw XML rows to list of dicts for Supabase insert."""
    rows = []
    for item in raw:
        if not item.get('Numero'):
            continue
        # Enrich with vereador name and partido from the lookup
        vid = item.get('Vereador', '')
        info = vereadores.get(vid, {})
        item['_nome'] = info.get('nome', f'Vereador {vid}')
        item['_partido'] = info.get('partido')
        rows.append(normalize_vereador_row(item, ano=ano))
    return rows


def ingest(ano: int, dry_run: bool = False):
    print(f"Fetching vereadores list for ano={ano}...")
    vereadores = fetch_vereadores(ano)
    print(f"Found {len(vereadores)} vereadores")

    raw = fetch_data(ano)
    rows = build_rows(raw, ano, vereadores)

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
