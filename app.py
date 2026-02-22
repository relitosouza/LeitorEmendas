from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import numpy as np
import os
import io
import math
import pdfplumber

app = Flask(__name__)

# Detectar ambiente Vercel (filesystem read-only exceto /tmp)
IS_VERCEL = os.environ.get('VERCEL', False)

# Pasta para persistir arquivos carregados
if IS_VERCEL:
    DATA_DIR = '/tmp/data'
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Dicionário global: {ano: DataFrame}
global_dfs = {}
# Ano atualmente selecionado
current_year = None

# Função para limpar valores não serializáveis em JSON (NaN, NaT, Timestamp, etc.)
def safe_val(val, default='-'):
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        f = float(val)
        return default if math.isnan(f) else f
    if pd.isna(val):
        return default
    return val

# Função utilitária sugerida para extrair a moeda para float
def parse_moeda(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).replace('R$', '').strip()
    
    # Tratando formato com possíveis problemas como `1.000,50` 
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
             val_str = val_str.replace('.', '').replace(',', '.')
        else:
             val_str = val_str.replace(',', '')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
        
    try:
        return float(val_str)
    except:
        return 0.0

def process_dataframe(df):
    """Processa um DataFrame bruto: normaliza colunas, parseia valores, etc."""
    # Colunas do portal da transparência que devem ser ignoradas
    # (reconhecidas para não interferir no mapeamento das demais)
    colunas_ignoradas = set()
    columns_list = list(df.columns)
    for col in columns_list:
        lower_col = str(col).lower().strip()
        if 'órgão processador' in lower_col or 'orgao processador' in lower_col:
            colunas_ignoradas.add(col)
        elif 'primeira fase' in lower_col or 'substituída' in lower_col or 'substituida' in lower_col:
            colunas_ignoradas.add(col)
        elif 'natureza' in lower_col:
            colunas_ignoradas.add(col)
        elif 'valor remanejado' in lower_col:
            colunas_ignoradas.add(col)

    col_mapper = {}
    mapped_values = set()

    # PASSADA 1: mapeamentos específicos (termos exatos/compostos)
    for col in columns_list:
        if col in colunas_ignoradas:
            continue
        lower_col = str(col).lower().strip()
        if 'nome' not in mapped_values and ('parlamentar' in lower_col or 'deputad' in lower_col or 'autor' in lower_col):
            col_mapper[col] = 'nome'
            mapped_values.add('nome')
        elif 'valor' not in mapped_values and ('valor decisão' in lower_col or 'valor decisao' in lower_col):
            col_mapper[col] = 'valor'
            mapped_values.add('valor')
        elif 'municipio' not in mapped_values and ('município' in lower_col or 'municipio' in lower_col):
            col_mapper[col] = 'municipio'
            mapped_values.add('municipio')
        elif 'funcao' not in mapped_values and ('função de governo' in lower_col or 'função' in lower_col or 'funcao' in lower_col):
            col_mapper[col] = 'funcao'
            mapped_values.add('funcao')
        elif 'data' not in mapped_values and 'data pagamento' in lower_col:
            col_mapper[col] = 'data'
            mapped_values.add('data')
        elif 'orgao' not in mapped_values and ('beneficiário' in lower_col or 'beneficiario' in lower_col):
            col_mapper[col] = 'orgao'
            mapped_values.add('orgao')
        elif 'status' not in mapped_values and ('estágio' in lower_col or 'estagio' in lower_col):
            col_mapper[col] = 'status'
            mapped_values.add('status')
        elif 'partido' not in mapped_values and 'partido' in lower_col:
            col_mapper[col] = 'partido'
            mapped_values.add('partido')
        elif 'codigo' not in mapped_values and ('código' in lower_col or 'codigo' in lower_col):
            col_mapper[col] = 'codigo'
            mapped_values.add('codigo')
        elif 'objeto' not in mapped_values and 'objeto' in lower_col:
            col_mapper[col] = 'objeto'
            mapped_values.add('objeto')

    # PASSADA 2: mapeamentos genéricos (só colunas não ignoradas e não mapeadas)
    for col in columns_list:
        if col in col_mapper or col in colunas_ignoradas:
            continue
        lower_col = str(col).lower().strip()
        if 'nome' not in mapped_values and 'nome' in lower_col and 'município' not in lower_col and 'municipio' not in lower_col:
            col_mapper[col] = 'nome'
            mapped_values.add('nome')
        elif 'valor' not in mapped_values and 'valor' in lower_col:
            col_mapper[col] = 'valor'
            mapped_values.add('valor')
        elif 'orgao' not in mapped_values and ('órgão' in lower_col or 'orgao' in lower_col):
            col_mapper[col] = 'orgao'
            mapped_values.add('orgao')
        elif 'data' not in mapped_values and 'data' in lower_col:
            col_mapper[col] = 'data'
            mapped_values.add('data')

    df = df.rename(columns=col_mapper)

    if 'nome' in df.columns:
        df['nome'] = df['nome'].astype(str).str.strip()
    if 'valor' in df.columns:
        df['valor_num'] = df['valor'].apply(parse_moeda)
    if 'status' in df.columns:
        df['pago_flag'] = df['status'].astype(str).str.lower().str.contains('pago')
    else:
        df['pago_flag'] = False

    return df

def extract_dataframe_from_pdf(file_stream):
    """Extrai tabelas de um PDF e tenta converter em um DataFrame consolidado."""
    all_rows = []
    
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            # Extrai tabelas da página (pode haver mais de uma)
            tables = page.extract_tables()
            for table in tables:
                # O table é uma lista de listas (linhas -> colunas)
                # Removendo linhas totalmente vazias ou nulas
                cleaned_table = [row for row in table if row and any(cell and cell.strip() for cell in row)]
                all_rows.extend(cleaned_table)
                
    if not all_rows:
         raise ValueError("Nenhuma tabela encontrada no PDF.")
         
    # Tenta usar a primeira linha preenchida como cabeçalho
    # Caso o título principal puxe a primeira linha da tabela, precisamos achar a linha correta dos cabeçalhos
    header_idx = -1
    for i, row in enumerate(all_rows[:20]): # Procura nas 20 primeiras linhas do documento
        row_str = ' '.join([str(c).upper() for c in row if c])
        if 'PARLAMENTAR' in row_str and ('VALOR' in row_str or 'MUNICÍPIO' in row_str or 'MUNICIPIO' in row_str or 'BENEFICI' in row_str):
            header_idx = i
            break

    if header_idx == -1:
        header_idx = 0

    header = all_rows[header_idx]
    
    # Sanitiza nomes das colunas para evitar erros de Null columns
    clean_header = []
    for i, h in enumerate(header):
        val = str(h).replace('\n', ' ').strip().upper() if h else f"COLUNA_{i}"
        clean_header.append(val)
        
    data = all_rows[header_idx+1:]
    
    # Filtra quebras de página contendo títulos ou cabeçalhos repetidos
    valid_data = []
    for row in data:
        row_str = ' '.join([str(c).upper() for c in row if c])
        # Pula cabeçalhos repetidos
        if 'PARLAMENTAR' in row_str and ('VALOR' in row_str or 'MUNICÍPIO' in row_str or 'MUNICIPIO' in row_str or 'BENEFICI' in row_str):
            continue
        # Pula títulos da página que escapem da tabela principal
        if 'EMENDAS IMPOSITIVAS' in row_str:
            continue
            
        valid_data.append(row)
    
    # Montando DataFrame
    df = pd.DataFrame(valid_data, columns=clean_header)
    return df


def process_pdf_dataframe(df):
    """Processa especificamente o DataFrame gerado via PDF (versões anteriores a 2022)."""
    # Limpa nomes das colunas
    df.columns = [str(c).strip().upper() for c in df.columns]

    col_mapper = {}
    for col in df.columns:
        if 'PARLAMENTAR' in col: col_mapper[col] = 'nome'
        elif 'BENEFICIÁRIO' in col or 'BENEFICIARIO' in col: col_mapper[col] = 'orgao'
        elif 'MUNICÍPIO' in col or 'MUNICIPIO' in col: col_mapper[col] = 'municipio'
        elif 'OBJETO' in col: col_mapper[col] = 'objeto'
        elif 'VALOR' in col: col_mapper[col] = 'valor'
        elif 'STATUS' in col: col_mapper[col] = 'status'
        # ÓRGÃO PROCESSADOR será ignorado

    df = df.rename(columns=col_mapper)

    # Preenche colunas obrigatórias faltantes para o frontend não quebrar
    for missing_col in ['partido', 'codigo', 'data', 'funcao']:
        if missing_col not in df.columns:
            df[missing_col] = '-'

    if 'nome' in df.columns:
        df['nome'] = df['nome'].astype(str).str.strip()
    if 'valor' in df.columns:
        df['valor_num'] = df['valor'].apply(parse_moeda)
    if 'status' in df.columns:
        df['pago_flag'] = df['status'].astype(str).str.lower().str.contains('pago')
    else:
        df['pago_flag'] = False

    return df



def load_saved_files():
    """Carrega todos os arquivos salvos na pasta data/ ao iniciar o servidor."""
    global global_dfs, current_year
    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(filepath, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(filepath, encoding='latin-1')
                df = process_dataframe(df)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(filepath)
                df = process_dataframe(df)
            elif filename.endswith('.pdf'):
                with open(filepath, 'rb') as f:
                     df = extract_dataframe_from_pdf(f)
                df = process_pdf_dataframe(df)
            else:
                continue

            # Extrair ano do nome do arquivo (ex: "2024.csv" -> "2024")
            ano = os.path.splitext(filename)[0]
            global_dfs[ano] = df
            print(f"[Startup] Carregado: {filename} ({len(df)} registros)")
        except Exception as e:
            print(f"[Startup] Erro ao carregar {filename}: {e}")

    if global_dfs and current_year is None:
        current_year = sorted(global_dfs.keys(), reverse=True)[0]
        print(f"[Startup] Ano ativo: {current_year}")


# Carregar dados salvos na inicialização
load_saved_files()

# CORS manual simplório (não restrito)
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/api/upload', methods=['POST'])
def upload_csv():
    global global_dfs, current_year

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Ano informado pelo frontend (default: extrair do nome do arquivo ou usar 'geral')
    ano = request.form.get('ano', '').strip()

    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx') or file.filename.endswith('.xls') or file.filename.endswith('.pdf')):
        file_stream = file.read()

        try:
            # Lendo CSV ou Excel com pandas
            if file.filename.endswith('.csv'):
                try:
                    df = pd.read_csv(io.BytesIO(file_stream), encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(file_stream), encoding='latin-1')
                df = process_dataframe(df)
            elif file.filename.endswith('.pdf'):
                df = extract_dataframe_from_pdf(io.BytesIO(file_stream))
                df = process_pdf_dataframe(df)
            else:
                df = pd.read_excel(io.BytesIO(file_stream))
                df = process_dataframe(df)

            # Detectar ano se não informado
            if not ano:
                if 'ANO' in [c.upper() for c in df.columns]:
                    ano_col = [c for c in df.columns if c.upper() == 'ANO'][0]
                    ano = str(int(df[ano_col].mode().iloc[0]))
                else:
                    ano = os.path.splitext(file.filename)[0]

            # Salvar arquivo original em disco para persistência
            ext = os.path.splitext(file.filename)[1]
            save_path = os.path.join(DATA_DIR, f"{ano}{ext}")
            with open(save_path, 'wb') as f:
                f.write(file_stream)

            global_dfs[ano] = df
            current_year = ano

            return jsonify({
                "success": True,
                "message": f"Arquivo processado e salvo para o ano {ano}",
                "count": len(df),
                "ano": ano,
                "anos_disponiveis": sorted(global_dfs.keys(), reverse=True)
            })
        except Exception as e:
            return jsonify({"error": f"Erro processando arquivo: {str(e)}"}), 500

    return jsonify({"error": "Apenas arquivos .csv, .xls, .xlsx ou .pdf são válidos"}), 400

@app.route('/api/anos')
def listar_anos():
    """Retorna a lista de anos disponíveis e o ano atual."""
    return jsonify({
        "anos": sorted(global_dfs.keys(), reverse=True),
        "current": current_year
    })


@app.route('/api/ano/<ano>', methods=['POST'])
def selecionar_ano(ano):
    """Seleciona o ano ativo."""
    global current_year
    if ano not in global_dfs:
        return jsonify({"error": f"Ano {ano} não encontrado"}), 404
    current_year = ano
    return jsonify({"success": True, "ano": ano, "count": len(global_dfs[ano])})


@app.route('/api/parlamentar/<path:query>')
def get_parlamentar_data(query):
    global current_year

    if not global_dfs or current_year is None:
        return jsonify({"error": "Nenhum arquivo carregado no servidor ainda"}), 400

    # Pegar ano do query param ou usar o atual
    ano = request.args.get('ano', current_year)
    if ano not in global_dfs:
        return jsonify({"error": f"Dados do ano {ano} não disponíveis"}), 400

    global_df = global_dfs[ano]
    query_lower = query.lower().strip()

    if 'nome' not in global_df.columns:
         return jsonify({"error": "Coluna de parlamentar não detectada no CSV"}), 400

    # Filtro Pandas para strings (regex=False para busca literal segura)
    mask = global_df['nome'].astype(str).str.strip().str.lower().str.contains(query_lower, na=False, regex=False)
    filtered_df = global_df[mask]

    if len(filtered_df) == 0:
        return jsonify({"error": "Nenhum parlamentar encontrado"}), 404
        
    # Informações Básicas
    first_record = filtered_df.iloc[0]
    nome_real = safe_val(first_record['nome'], 'N/A') if 'nome' in filtered_df.columns else "N/A"
    partido_real = safe_val(first_record['partido'], '-') if 'partido' in filtered_df.columns else "-"
    
    # Cálculos PANDAS (Rápidos e Eficientes)
    total_val = float(filtered_df['valor_num'].sum()) if 'valor_num' in filtered_df.columns else 0.0
    total_pagos = float(filtered_df[filtered_df['pago_flag']]['valor_num'].sum()) if 'pago_flag' in filtered_df.columns and 'valor_num' in filtered_df.columns else 0.0
    
    pct_pago = (total_pagos / total_val * 100) if total_val > 0 else 0
    
    # Agrupamentos (Top Ranking por Valor Numérico)
    # Munícipios
    top_mun = {}
    if 'municipio' in filtered_df.columns and 'valor_num' in filtered_df.columns:
        mun_grp = filtered_df.groupby('municipio')['valor_num'].sum().reset_index()
        mun_sorted = mun_grp.sort_values(by='valor_num', ascending=False)
        for _, row in mun_sorted.iterrows():
            top_mun[str(safe_val(row['municipio'], 'N/A'))] = float(safe_val(row['valor_num'], 0))

    # Setor Prioritário (Função) — até 2 setores se empatarem no topo
    top_func = {}
    setores_prioritarios = []

    if 'funcao' in filtered_df.columns and 'valor_num' in filtered_df.columns:
        func_grp = filtered_df.groupby('funcao')['valor_num'].sum().reset_index()
        func_sorted = func_grp.sort_values(by='valor_num', ascending=False)

        if len(func_sorted) > 0:
            top_val = float(safe_val(func_sorted.iloc[0]['valor_num'], 0))
            # Pegar todos os setores que empatam com o maior valor (máximo 2)
            for _, row in func_sorted.iterrows():
                row_val = float(safe_val(row['valor_num'], 0))
                if row_val == top_val and len(setores_prioritarios) < 2:
                    setores_prioritarios.append({
                        "nome": str(safe_val(row['funcao'], '-')),
                        "valor": row_val
                    })
                else:
                    break

        for _, row in func_sorted.iterrows():
            top_func[str(safe_val(row['funcao'], 'N/A'))] = float(safe_val(row['valor_num'], 0))

    # Tabela Histórico Sortida
    historico = []
    hist_sorted = filtered_df.sort_values(by='valor_num', ascending=False)
    for _, row in hist_sorted.iterrows():
        historico.append({
            "data": str(safe_val(row.get('data', '-'))),
            "codigo": str(safe_val(row.get('codigo', ''), '')),
            "municipio": str(safe_val(row.get('municipio', ''), '')),
            "objeto": str(safe_val(row.get('objeto', ''), '')),
            "destino": str(safe_val(row.get('orgao', ''), '')),
            "status": str(safe_val(row.get('status', ''), '')),
            "is_pago": bool(row.get('pago_flag', False)),
            "valor_raw": float(safe_val(row.get('valor_num', 0), 0))
        })
    
    return jsonify({
        "success": True,
        "parlamentar": {
            "nome": nome_real,
            "partido": partido_real,
        },
        "indicadores": {
            "total_indicado": total_val,
            "count": len(filtered_df),
            "execucao_pago": pct_pago,
            "setor_prioritario": setores_prioritarios
        },
        "top_municipios": top_mun,
        "todas_funcoes": top_func,
        "historico": historico
    })


@app.route('/')
def index():
    # Helper to return the HTML statically
    with open('index.html', 'r', encoding='utf-8') as f:
         return render_template_string(f.read())
         
if __name__ == '__main__':
    app.run(debug=True, port=5000)
