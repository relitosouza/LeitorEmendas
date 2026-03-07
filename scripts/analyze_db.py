import os
from dotenv import load_dotenv
from collections import Counter

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_utils import get_supabase_client

load_dotenv()
client = get_supabase_client()

all_rows = []
offset = 0
batch_size = 1000

while True:
    result = client.table('emendas').select('ano, tipo').range(offset, offset + batch_size - 1).execute()
    
    if not result.data:
        break
        
    all_rows.extend(result.data)
    
    if len(result.data) < batch_size:
        break
        
    offset += batch_size

print(f"Total rows fetched: {len(all_rows)}")

counts = Counter((row['ano'], row['tipo']) for row in all_rows)

for (ano, tipo), count in sorted(counts.items()):
    print(f"Ano: {ano} | Tipo: {tipo} | Total: {count}")

