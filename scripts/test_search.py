import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

# Search
q = supabase.table('emendas').select('*').or_(f"nome.ilike.%kim%,beneficiario.ilike.%kim%").limit(10)
res = q.execute()

print(f"Total encontrados: {len(res.data)}")
for d in res.data:
    print(f"- {d.get('ano')} | {d.get('municipio')} | R$ {d.get('valor')} | {d.get('objeto')} | {d.get('status')} | pago: {d.get('pago')}")
