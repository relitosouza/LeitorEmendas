import requests
import json

def buscar_deputado(nome):
    print(f"\n========================================================")
    print(f"Buscando deputado(a): '{nome}' na API de Dados Abertos...")
    print(f"========================================================")
    
    # Endpoint público da Câmara dos Deputados, sem necessidade de token
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    
    # Parâmetros da busca
    params = {
        "nome": nome,
        "ordem": "ASC",
        "ordenarPor": "nome"
    }
    
    try:
        # Fazendo a requisição HTTP GET (Sem headers de autorização)
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            dados = response.json().get('dados', [])
            
            if not dados:
                print("❌ Nenhum deputado encontrado com esse nome na atual legislatura.")
                return

            print(f"✅ Encontrado(s) {len(dados)} deputado(s)!")
            for dep in dados:
                print("\n👤 INFORMAÇÕES DO PARLAMENTAR:")
                print(f"Nome Parlamentar : {dep.get('nome')}")
                print(f"Partido - Estado : {dep.get('siglaPartido')} - {dep.get('siglaUf')}")
                print(f"ID no Sistema    : {dep.get('id')}")
                print(f"E-mail           : {dep.get('email')}")
                print(f"Foto Oficial     : {dep.get('urlFoto')}")
                
                # Exemplo de como você poderia usar o ID para buscar detalhes como despesas ou proposições do deputado
                print(f"Link API Detalhes: {dep.get('uri')}")
                
        else:
            print(f"❌ Erro na requisição: Status {response.status_code}")
            
    except Exception as e:
         print(f"❌ Erro de conexão: {e}")

if __name__ == "__main__":
    # Testando com alguns nomes comuns
    buscar_deputado("Tiririca")
    buscar_deputado("Tabata")
