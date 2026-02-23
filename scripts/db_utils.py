import os
import math
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def parse_moeda(val) -> float:
    """Convert Brazilian currency string or number to float."""
    if val is None:
        return 0.0
    if isinstance(val, float):
        return 0.0 if math.isnan(val) else val
    if isinstance(val, (int,)):
        return float(val)
    val_str = str(val).replace('R$', '').strip()
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0


def _safe(val, default=None):
    """Return None for NaN/NaT, otherwise the value."""
    if val is None:
        return default
    if isinstance(val, float) and math.isnan(val):
        return default
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


def normalize_deputado_row(row: dict, ano: int) -> dict:
    """Convert a processed DataFrame row (dict) to an emendas table row."""
    data_val = _safe(row.get('data'))
    if data_val and data_val != '-':
        try:
            data_val = str(pd.to_datetime(data_val).date())
        except Exception:
            data_val = None
    else:
        data_val = None

    return {
        'tipo': 'deputado',
        'nome': str(row.get('nome', '')).strip(),
        'partido': _safe(row.get('partido')),
        'ano': ano,
        'municipio': _safe(row.get('municipio')),
        'funcao': _safe(row.get('funcao')),
        'beneficiario': _safe(row.get('orgao')),
        'objeto': _safe(row.get('objeto')),
        'codigo': _safe(row.get('codigo')),
        'status': _safe(row.get('status')),
        'data_pago': data_val,
        'valor': float(row.get('valor_num', 0.0) or 0.0),
        'pago': bool(row.get('pago_flag', False)),
    }


def normalize_vereador_row(row: dict, ano: int) -> dict:
    """
    Convert a vereador JSON API row to an emendas table row.
    Field mapping: adjust 'nome_vereador' key to match the real API field name.
    """
    nome = (
        row.get('nome_vereador')
        or row.get('nome_parlamentar')
        or row.get('nome')
        or ''
    )
    status = str(row.get('status', '')).lower()
    pago = 'pago' in status

    data_val = _safe(row.get('data_pagamento') or row.get('data_pago'))
    if data_val:
        try:
            data_val = str(pd.to_datetime(data_val).date())
        except Exception:
            data_val = None

    return {
        'tipo': 'vereador',
        'nome': str(nome).strip(),
        'partido': _safe(row.get('partido')),
        'ano': ano,
        'municipio': _safe(row.get('municipio')),
        'funcao': _safe(row.get('funcao') or row.get('funcao_governo')),
        'beneficiario': _safe(row.get('beneficiario') or row.get('orgao')),
        'objeto': _safe(row.get('objeto') or row.get('descricao')),
        'codigo': _safe(row.get('codigo') or row.get('id')),
        'status': _safe(row.get('status')),
        'data_pago': data_val,
        'valor': parse_moeda(row.get('valor') or row.get('valor_decisao', 0)),
        'pago': pago,
    }
