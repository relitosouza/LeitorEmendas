import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.db_utils import parse_moeda, normalize_deputado_row, normalize_vereador_row


def test_parse_moeda_string_br():
    assert parse_moeda("1.234,56") == 1234.56


def test_parse_moeda_string_r():
    assert parse_moeda("R$ 500,00") == 500.00


def test_parse_moeda_float():
    assert parse_moeda(1000.0) == 1000.0


def test_parse_moeda_nan():
    import math
    assert parse_moeda(float('nan')) == 0.0


def test_normalize_deputado_row_basic():
    row = {
        'nome': 'João Silva',
        'partido': 'PT',
        'ano': 2024,
        'municipio': 'São Paulo',
        'funcao': 'Saúde',
        'orgao': 'Hospital X',
        'objeto': 'Equipamentos',
        'codigo': 'EMD-001',
        'status': 'Pago',
        'data': '2024-03-15',
        'valor_num': 50000.0,
        'pago_flag': True,
    }
    result = normalize_deputado_row(row, ano=2024)
    assert result['tipo'] == 'deputado'
    assert result['nome'] == 'João Silva'
    assert result['pago'] == True
    assert result['valor'] == 50000.0
    assert result['ano'] == 2024


def test_normalize_deputado_row_missing_fields():
    row = {'nome': 'Maria', 'valor_num': 0.0, 'pago_flag': False}
    result = normalize_deputado_row(row, ano=2023)
    assert result['tipo'] == 'deputado'
    assert result['partido'] is None
    assert result['municipio'] is None


def test_normalize_vereador_row_basic():
    row = {
        'nome_vereador': 'Carlos Souza',
        'partido': 'PSDB',
        'ano': 2024,
        'municipio': 'São Paulo',
        'valor': 30000.0,
        'status': 'pago',
        'objeto': 'Obras',
        'codigo': 'VER-001',
    }
    result = normalize_vereador_row(row, ano=2024)
    assert result['tipo'] == 'vereador'
    assert result['nome'] == 'Carlos Souza'
    assert result['pago'] == True
