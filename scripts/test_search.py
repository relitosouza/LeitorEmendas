import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

# Search
query = "marcos"
q = supabase.table('emendas').select('nome').ilike('nome', f'%{query}%').limit(10)
res = q.execute()

nomes_unicos = set(r['nome'] for r in res.data)
print(f"Nomes encontrados contendo '{query}':")
for n in nomes_unicos:
    print(n)
