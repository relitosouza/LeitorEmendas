from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import numpy as np
import os
import requests
import math
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

# ── Supabase client ──────────────────────────────────────────────────────────
_supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


# ── Utilities ────────────────────────────────────────────────────────────────
def safe_val(val, default='-'):
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        f = float(val)
        return default if math.isnan(f) else f
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    return val

def get_camara_info(nome):
    try:
        url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
        params = {"nome": nome, "ordem": "ASC", "ordenarPor": "nome"}
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            dados = resp.json().get('dados', [])
            if dados:
                return {
                    "foto": dados[0].get('urlFoto', ''),
                    "partido": dados[0].get('siglaPartido', ''),
                    "uf": dados[0].get('siglaUf', '')
                }
    except Exception:
        pass
    return None


# ── CORS ─────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route('/api/anos')
def listar_anos():
    """Return distinct years available in the database."""
    # Fetch all anos in batches to avoid Supabase default 1000-row limit
    all_anos = set()
    offset = 0
    batch_size = 1000
    while True:
        result = (_supabase.table('emendas')
                  .select('ano')
                  .range(offset, offset + batch_size - 1)
                  .execute())
        if not result.data:
            break
        all_anos.update(row['ano'] for row in result.data)
        if len(result.data) < batch_size:
            break
        offset += batch_size
    anos = sorted(all_anos, reverse=True)
    return jsonify({"anos": anos})


@app.route('/api/parlamentar/<path:query>')
def get_parlamentar_data(query):
    query_lower = query.lower().strip()
    ano = request.args.get('ano')

    q = _supabase.table('emendas').select('*').ilike('nome', f'%{query_lower}%').limit(5000)
    result = q.execute()
    rows = result.data

    if not rows:
        return jsonify({"error": "Nenhum parlamentar encontrado"}), 404

    if ano:
        rows = [r for r in rows if str(r.get('ano', '')) == str(ano)]
        if not rows:
            return jsonify({"error": f"Parlamentar sem dados para o ano {ano}"}), 404

    df = pd.DataFrame(rows)
    df['valor_num'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    df['pago_flag'] = df['pago'].astype(bool)

    first = df.iloc[0]
    nome_real = safe_val(first.get('nome'), 'N/A')
    partido_real = safe_val(first.get('partido'), '-')
    tipo_real = safe_val(first.get('tipo'), 'deputado')

    foto_url = ""
    uf_real = ""

    if tipo_real.lower() == 'deputado':
        camara_info = get_camara_info(nome_real)
        if camara_info:
            foto_url = camara_info.get('foto', '')
            if camara_info.get('partido'):
                partido_real = camara_info['partido']
            uf_real = camara_info.get('uf', '')

    total_val = float(df['valor_num'].sum())
    total_pagos = float(df[df['pago_flag']]['valor_num'].sum())
    pct_pago = (total_pagos / total_val * 100) if total_val > 0 else 0

    # Top municipalities
    top_mun = {}
    if 'municipio' in df.columns:
        mun_grp = df.groupby('municipio')['valor_num'].sum().reset_index()
        for _, row in mun_grp.sort_values('valor_num', ascending=False).iterrows():
            top_mun[str(safe_val(row['municipio'], 'N/A'))] = float(safe_val(row['valor_num'], 0))

    # Priority sector
    setores_prioritarios = []
    top_func = {}
    if 'funcao' in df.columns:
        func_grp = df.groupby('funcao')['valor_num'].sum().reset_index()
        func_sorted = func_grp.sort_values('valor_num', ascending=False)
        if len(func_sorted) > 0:
            top_val = float(safe_val(func_sorted.iloc[0]['valor_num'], 0))
            for _, row in func_sorted.iterrows():
                row_val = float(safe_val(row['valor_num'], 0))
                if row_val == top_val and len(setores_prioritarios) < 2:
                    setores_prioritarios.append({"nome": str(safe_val(row['funcao'], '-')), "valor": row_val})
                else:
                    break
        for _, row in func_sorted.iterrows():
            top_func[str(safe_val(row['funcao'], 'N/A'))] = float(safe_val(row['valor_num'], 0))

    # History table
    historico = []
    for _, row in df.sort_values('valor_num', ascending=False).iterrows():
        historico.append({
            "data": str(safe_val(row.get('data_pago', '-'))),
            "codigo": str(safe_val(row.get('codigo', ''), '')),
            "municipio": str(safe_val(row.get('municipio', ''), '')),
            "objeto": str(safe_val(row.get('objeto', ''), '')),
            "destino": str(safe_val(row.get('beneficiario', ''), '')),
            "status": str(safe_val(row.get('status', ''), '')),
            "natureza": str(safe_val(row.get('natureza', ''), '')),
            "is_pago": bool(row.get('pago_flag', False)),
            "valor_raw": float(safe_val(row.get('valor_num', 0), 0)),
        })

    return jsonify({
        "success": True,
        "parlamentar": {
            "nome": nome_real,
            "partido": partido_real,
            "tipo": tipo_real,
            "foto": foto_url,
            "uf": uf_real
        },
        "indicadores": {
            "total_indicado": total_val,
            "count": len(df),
            "execucao_pago": pct_pago,
            "setor_prioritario": setores_prioritarios,
        },
        "top_municipios": top_mun,
        "todas_funcoes": top_func,
        "historico": historico,
    })


@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return render_template_string(f.read())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
