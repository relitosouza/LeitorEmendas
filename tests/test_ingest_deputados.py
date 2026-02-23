import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from scripts.ingest_deputados import load_file, build_rows


def test_load_xlsx_returns_dataframe(tmp_path):
    # Create a minimal XLSX with expected columns
    df = pd.DataFrame({
        'PARLAMENTAR': ['João Silva'],
        'PARTIDO': ['PT'],
        'ANO': [2024],
        'MUNICÍPIO': ['São Paulo'],
        'VALOR DECISÃO': ['R$ 10.000,00'],
        'ESTÁGIO': ['Pago'],
    })
    xlsx_path = tmp_path / "2024.xlsx"
    df.to_excel(xlsx_path, index=False)

    result = load_file(str(xlsx_path))
    assert isinstance(result, pd.DataFrame)
    assert 'nome' in result.columns
    assert 'valor_num' in result.columns


def test_build_rows_returns_list_of_dicts():
    df = pd.DataFrame({
        'nome': ['João Silva'],
        'partido': ['PT'],
        'municipio': ['São Paulo'],
        'valor_num': [10000.0],
        'pago_flag': [True],
        'status': ['Pago'],
    })
    rows = build_rows(df, ano=2024)
    assert len(rows) == 1
    assert rows[0]['tipo'] == 'deputado'
    assert rows[0]['nome'] == 'João Silva'
    assert rows[0]['ano'] == 2024


def test_build_rows_skips_empty_names():
    df = pd.DataFrame({
        'nome': ['', '  ', 'Maria'],
        'valor_num': [0.0, 0.0, 5000.0],
        'pago_flag': [False, False, False],
    })
    rows = build_rows(df, ano=2024)
    assert len(rows) == 1
    assert rows[0]['nome'] == 'Maria'
