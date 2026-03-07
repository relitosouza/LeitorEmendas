import os
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_utils import get_supabase_client

load_dotenv()
client = get_supabase_client()

print("Atualizando registros de 'deputado' para 'deputado estadual'...")

# Como a biblioteca Supabase (Postgrest) em Python não suporta update() sem filtros adequados para lotes maiores que o limite,
# precisamos atualizar usando um critério simples:
response = client.table('emendas').update({'tipo': 'deputado estadual'}).eq('tipo', 'deputado').eq('ano', 2023).execute()

print(f"Registros afetados/atualizados: {len(response.data)}")
print("Sucesso!")
