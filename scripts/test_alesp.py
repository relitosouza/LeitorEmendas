import requests

def test_alesp():
    print("Testing ALESP API...")
    url = "https://dadosabertos.al.sp.gov.br/api/v1/deputados"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # print first 2 deputies
            print("Found", len(data), "deputies:")
            for d in data[:2]:
                print(d)
        else:
            print("Status code:", resp.status_code)
    except Exception as e:
        print("Error:", e)

test_alesp()
