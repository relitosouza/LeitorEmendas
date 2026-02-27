import requests
import xml.etree.ElementTree as ET

def test_apis():
    print("--- ALESP ---")
    url_alesp = "https://www.al.sp.gov.br/repositorioDados/deputados/deputados.xml"
    try:
        r = requests.get(url_alesp)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Content excerpt:", r.text[:500])
        else:
            print("ALESP FAIL", r.status_code)
    except Exception as e:
        print("ALESP Error", e)

test_apis()
