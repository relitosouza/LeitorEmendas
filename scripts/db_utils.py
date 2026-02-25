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
        'natureza': _safe(row.get('natureza')),
        'data_pago': data_val,
        'valor': float(row.get('valor_num', 0.0) or 0.0),
        'pago': bool(row.get('pago_flag', False)),
    }


# Classificação funcional da despesa pública (Portaria MOG nº 42/1999)
FUNCOES_GOVERNO = {
    '01': '01 - Legislativa',
    '02': '02 - Judiciária',
    '03': '03 - Essencial à Justiça',
    '04': '04 - Administração',
    '05': '05 - Defesa Nacional',
    '06': '06 - Segurança Pública',
    '07': '07 - Relações Exteriores',
    '08': '08 - Assistência Social',
    '09': '09 - Previdência Social',
    '10': '10 - Saúde',
    '11': '11 - Trabalho',
    '12': '12 - Educação',
    '13': '13 - Cultura',
    '14': '14 - Direitos da Cidadania',
    '15': '15 - Urbanismo',
    '16': '16 - Habitação',
    '17': '17 - Saneamento',
    '18': '18 - Gestão Ambiental',
    '19': '19 - Ciência e Tecnologia',
    '20': '20 - Agricultura',
    '21': '21 - Organização Agrária',
    '22': '22 - Indústria',
    '23': '23 - Comércio e Serviços',
    '24': '24 - Comunicações',
    '25': '25 - Energia',
    '26': '26 - Transporte',
    '27': '27 - Desporto e Lazer',
    '28': '28 - Encargos Especiais',
    '99': '99 - Reserva de Contingência',
}


def normalize_vereador_row(row: dict, ano: int) -> dict:
    """
    Convert a vereador XML API row to an emendas table row.
    XML fields: Numero, Vereador (ID), DataEmenda, IdExercEmp, Motivo
    Enriched fields: _nome (from Vereadores API), _partido
    """
    nome = str(row.get('_nome') or row.get('Vereador') or '').strip()

    data_val = _safe(row.get('DataEmenda'))
    if data_val:
        try:
            data_val = str(pd.to_datetime(data_val, dayfirst=True).date())
        except Exception:
            data_val = None

    valor = float(row.get('_valor', 0) or 0)

    return {
        'tipo': 'vereador',
        'nome': nome,
        'partido': _safe(row.get('_partido')),
        'ano': ano,
        'municipio': 'São Paulo',
        'funcao': FUNCOES_GOVERNO.get(str(row.get('_funcao', '')).strip(), _safe(row.get('_funcao'))),
        'beneficiario': None,
        'objeto': _safe(row.get('Motivo')),
        'codigo': _safe(row.get('Numero')),
        'status': None,
        'natureza': 'Impositiva',
        'data_pago': data_val,
        'valor': valor,
        'pago': valor > 0,
    }
