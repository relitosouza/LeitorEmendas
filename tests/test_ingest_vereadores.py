import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from scripts.ingest_vereadores import fetch_data, build_rows


def test_fetch_data_returns_list(requests_mock):
    sample = [{"nome": "Paulo Frange", "partido": "PTB", "valor": 10000}]
    requests_mock.get("https://fake-api.example.com/vereadores", json=sample)

    with patch.dict(os.environ, {"VEREADORES_API_URL": "https://fake-api.example.com/vereadores"}):
        result = fetch_data(ano=2024)
    assert isinstance(result, list)
    assert len(result) == 1


def test_build_rows_returns_correct_tipo():
    raw = [{"nome": "Ana Lima", "partido": "DEM", "valor": 5000.0, "status": "Pago"}]
    rows = build_rows(raw, ano=2024)
    assert rows[0]['tipo'] == 'vereador'
    assert rows[0]['nome'] == 'Ana Lima'


def test_build_rows_skips_empty_names():
    raw = [{"nome": "", "valor": 1000}, {"nome": "Carlos", "valor": 2000}]
    rows = build_rows(raw, ano=2024)
    assert len(rows) == 1
