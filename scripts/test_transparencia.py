import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("API_TRANSPARENCIA")

url = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
headers = {
    "chave-api-dados": api_key,
    "accept": "application/json"
}

params = {
    "ano": 2023,
    "pagina": 1,
    "localidadeDoGasto": "SÃO PAULO (UF)"
}

response = requests.get(url, headers=headers, params=params)
print("Status Code:", response.status_code)
try:
    data = response.json()
    if len(data) > 0:
        import json
        print("Sample:")
        print(json.dumps(data[0], indent=2, default=str))
except Exception as e:
    print("Error:", e)
