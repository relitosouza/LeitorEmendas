import os
import argparse
import requests
import json
from dotenv import load_dotenv

# Re-use our db_utils to insert data
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.db_utils import get_supabase_client, normalize_deputado_row

load_dotenv()

API_TRANSPARENCIA_URL = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
API_CAMARA_URL = "https://dadosabertos.camara.leg.br/api/v2/deputados"

def get_transparencia_headers():
    api_key = os.environ.get("API_TRANSPARENCIA")
    if not api_key:
        print("Error: API_TRANSPARENCIA is not set in .env")
        sys.exit(1)
    return {
        "chave-api-dados": api_key,
        "accept": "application/json"
    }

def fetch_sp_deputies():
    """Fetches list of authors (SP Federal Deputies) from Camara API"""
    print("Fetching SP Federal Deputies from Camara API...")
    try:
        # idLegislatura 57 = 2023-2026
        # idLegislatura 56 = 2019-2022
        # We fetch all the ones currently representing SP
        params = {"siglaUf": "SP", "itens": 100}
        r = requests.get(API_CAMARA_URL, params=params, timeout=15)
        r.raise_for_status()
        dados = r.json().get('dados', [])
        print(f"  Found {len(dados)} deputies for SP.")
        return dados
    except Exception as e:
        print("Error fetching deputies:", e)
        return []

def fetch_emendas_transparencia(ano, nome_autor):
    """Fetch all pages of amendments for a specific author and year."""
    headers = get_transparencia_headers()
    all_data = []
    pagina = 1
    
    while True:
        params = {
            "ano": ano,
            "nomeAutor": nome_autor,
            "pagina": pagina
        }
        try:
            r = requests.get(API_TRANSPARENCIA_URL, headers=headers, params=params, timeout=15)
            if r.status_code == 429: # Rate limit
                print("  Rate limit reached! Waiting 5s...")
                import time
                time.sleep(5)
                continue
                
            if r.status_code != 200:
                print(f"  Transparencia HTTP {r.status_code} for {nome_autor}")
                break
                
            data = r.json()
            if not data:
                break
                
            all_data.extend(data)
            
            # API da Transparencia pages by 15 records
            if len(data) < 15:
                break
            pagina += 1
            import time
            time.sleep(1) # Prevent heavy rate-limiting
        except Exception as e:
            print(f"  Error mapping {nome_autor}: {e}")
            break
            
    return all_data

def format_db_row(emenda, ano, row_id):
    """Converts the Portal da Transparencia API response into our standard DataFrame/dict format"""
    # Portal API outputs: 
    # valorEmpenhado, valorLiquidado, valorPago string formats ("6.467,00")
    
    # We will use the valorPago explicitly, or valorEmpenhado as the 'valor decisão'
    import re
    def parse_br_val(v):
        if not v: return 0.0
        v = str(v).replace('.', '').replace(',', '.')
        try:
            return float(v)
        except ValueError:
            return 0.0
            
    valor_pago = parse_br_val(emenda.get('valorPago'))
    valor_empenhado = parse_br_val(emenda.get('valorEmpenhado'))
    # Use empenhado as the target value, but flag pagamentos se valor_pago > 0
    valor_final = valor_empenhado if valor_empenhado > 0 else valor_pago

    # Mapeando os campos para a estrutura do banco através do db_utils (simulando linha do CSV)
    raw_dict = {
        'nome': emenda.get('nomeAutor', 'Desconhecido'),
        'partido': 'SP', # Infelizmente a Transparencia nao manda o partido e a tabela pede
        'municipio': str(emenda.get('localidadeDoGasto', '')).replace(' (UF)', '').strip(),
        'funcao': emenda.get('funcao'),
        'orgao': emenda.get('subfuncao'), # Usando subfuncao no lugar de orgao beneficiario caso não tenha beneficiario
        'objeto': f"{emenda.get('tipoEmenda', 'Emenda')} - {emenda.get('subfuncao', '')}",
        'codigo': emenda.get('codigoEmenda'),
        'status': 'Pago' if valor_pago > 0 else 'Empenhado' if valor_empenhado > 0 else 'Aguardando',
        'natureza': emenda.get('tipoEmenda'),
        'valor_num': valor_final,
        'pago_flag': valor_pago > 0,
        'data': '-'
    }
    
    return normalize_deputado_row(raw_dict, ano, tipo='deputado federal')

def run_ingestion(ano, dry_run=False):
    deputies = fetch_sp_deputies()
    if not deputies:
        print("Aborting because no deputies were found.")
        return
        
    print(f"Starting ingestion process for Federal Deputies / Year: {ano}")
    all_mapped_rows = []
    
    for count, dep in enumerate(deputies, 1):
        # We will query by the standard API name first
        author_name = dep.get('nome').upper()
        print(f"[{count}/{len(deputies)}] Fetching {author_name}...")
        
        emendas = fetch_emendas_transparencia(ano, author_name)
        
        # If no results, try the nomeCivil? 
        if not emendas and emendas != []:
            # Just means no data, skip
            continue
            
        for idx, em in enumerate(emendas):
             all_mapped_rows.append(format_db_row(em, ano, f"{idx}"))
             
    print(f"Finished fetching data. Extracted {len(all_mapped_rows)} amendments for ano={ano}.")
    
    if dry_run:
        print("[dry-run] Skipping database write.")
        if all_mapped_rows:
            import pprint
            print("Sample row:")
            pprint.pprint(all_mapped_rows[0])
        return

    if not all_mapped_rows:
        print("No rows to insert.")
        return

    client = get_supabase_client()
    
    # Excluíndo apenas federais daquele ano
    client.table('emendas').delete().eq('tipo', 'deputado federal').eq('ano', ano).execute()
    print(f"Deleted existing 'deputado federal' rows for ano={ano}")

    batch_size = 500
    for i in range(0, len(all_mapped_rows), batch_size):
        batch = all_mapped_rows[i:i + batch_size]
        client.table('emendas').insert(batch).execute()
        print(f"  Inserted batch {i // batch_size + 1} ({len(batch)} rows)")

    print(f"Done. Total inserted: {len(all_mapped_rows)} rows.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest Federal Deputies from Portal da Transparencia API')
    parser.add_argument('--ano', type=int, default=2023, help='Ano para processar')
    parser.add_argument('--dry-run', action='store_true', help='Não salva no banco de dados')
    args = parser.parse_args()
    
    run_ingestion(ano=args.ano, dry_run=args.dry_run)
