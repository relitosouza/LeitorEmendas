import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    # Mock Supabase before importing app to avoid needing real credentials
    with patch('supabase.create_client') as mock_create:
        mock_sb = MagicMock()
        mock_create.return_value = mock_sb
        os.environ.setdefault('SUPABASE_URL', 'https://fake.supabase.co')
        os.environ.setdefault('SUPABASE_KEY', 'fake-key')
        import importlib
        import app as flask_app
        importlib.reload(flask_app)
        flask_app.app.config['TESTING'] = True
        with flask_app.app.test_client() as c:
            yield c, mock_sb


def test_search_returns_404_when_no_rows(client):
    c, mock_sb = client
    mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value.data = []
    resp = c.get('/api/parlamentar/nonexistent')
    assert resp.status_code == 404


def test_search_returns_parlamentar_data(client):
    c, mock_sb = client
    fake_rows = [
        {
            'tipo': 'deputado', 'nome': 'João Silva', 'partido': 'PT',
            'ano': 2024, 'municipio': 'São Paulo', 'funcao': 'Saúde',
            'beneficiario': 'Hospital X', 'objeto': 'Equipamentos',
            'codigo': 'EMD-001', 'status': 'Pago', 'data_pago': '2024-03-15',
            'valor': 50000.0, 'pago': True,
        }
    ]
    mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value.data = fake_rows
    resp = c.get('/api/parlamentar/Jo%C3%A3o')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['parlamentar']['nome'] == 'João Silva'
    assert data['parlamentar']['tipo'] == 'deputado'
    assert 'indicadores' in data
    assert 'historico' in data


def test_anos_endpoint_returns_list(client):
    c, mock_sb = client
    mock_sb.table.return_value.select.return_value.execute.return_value.data = [
        {'ano': 2024}, {'ano': 2023}
    ]
    resp = c.get('/api/anos')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'anos' in data
    assert 2024 in data['anos']
