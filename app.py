import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import requests
import urllib3
from supabase import create_client

# Desativa avisos de certificado SSL ao conectar diretamente via IP
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# LEITURA ROBUSTA DE SEGREDOS (RENDER / STREAMLIT)
# ==========================================
def obter_segredo(chave, padrao=""):
    try:
        if chave in st.secrets:
            return st.secrets[chave]
    except Exception:
        pass
    return os.environ.get(chave, padrao)

SUPABASE_URL = obter_segredo("SUPABASE_URL")
SUPABASE_KEY = obter_segredo("SUPABASE_KEY")

@st.cache_resource
def init_connection():
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("As credenciais do Supabase não foram encontradas.")
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro crítico ao carregar as credenciais do Supabase: {e}")
        return None

supabase = init_connection()

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E ESTÉTICA HIGH-END
# ==========================================
st.set_page_config(page_title="ERP BM Make Up Store", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #f8fafc; }
    
    /* BLOQUEIO ABSOLUTO DE QUALQUER RODAPÉ, MARCA D'ÁGUA OU SELO FLUTUANTE */
    #MainMenu, footer, .stDeployButton {display: none !important; visibility: hidden !important;}
    div[data-testid="stStatusWidget"] {display: none !important; visibility: hidden !important;}
    .viewerBadge_container__1QSob, div.viewerBadge_link__1S137, ._profileContainer_gzau3_1, iframe[src*="streamlit"] {
        display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important;
    }
    div[class*="viewerBadge"], footer[class*="viewerBadge"] { display: none !important; }
    
    [data-testid="stImage"] img { mix-blend-mode: multiply; border-radius: 8px; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; padding-top: 1rem; }
    
    [data-testid="stSidebar"] .stButton>button {
        background: #ffffff !important; color: #475569 !important; border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important; padding: 0.7rem 1rem !important; font-weight: 600 !important;
        text-align: left !important; box-shadow: 0 1px 2px rgba(0,0,0,0.01) !important;
        transition: all 0.2s ease-in-out; width: 100% !important; margin-bottom: 6px;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        background: #fdf2f8 !important; color: #d91c84 !important; border-color: #fbcfe8 !important; transform: translateX(4px);
    }
    
    .main .stButton>button {
        background: linear-gradient(135deg, #d91c84 0%, #b01269 100%); color: white; border-radius: 8px; 
        padding: 0.6rem 1.2rem; font-weight: 600; border: none; box-shadow: 0 4px 12px rgba(217, 28, 132, 0.2); 
        transition: all 0.3s ease;
    }
    .main .stButton>button:hover {
        background: linear-gradient(135deg, #b01269 0%, #8c0d52 100%); box-shadow: 0 6px 15px rgba(217, 28, 132, 0.35);
    }
    
    div[data-testid="stMetric"] {
        background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label { color: #64748b !important; font-weight: 500; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #d91c84 !important; font-weight: 700; }
    h1, h2, h3 { color: #1e293b; font-weight: 700; margin-bottom: 0px; padding-bottom: 0px;}
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def encontrar_caminho_logo():
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    for arquivo in ["logo.png", "logo.png.png", "logo.jpg", "logo.jpeg"]:
        caminho = os.path.join(pasta_atual, arquivo)
        if os.path.exists(caminho): return caminho
    return None

caminho_oficial_logo = encontrar_caminho_logo()
if caminho_oficial_logo:
    try: st.logo(caminho_oficial_logo)
    except: pass

# ==========================================
# SISTEMA DE AUTENTICAÇÃO PERSISTENTE
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if "auth" in st.query_params and st.query_params["auth"] == "true":
    st.session_state.autenticado = True

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if caminho_oficial_logo: st.image(caminho_oficial_logo, width=180)
        st.markdown("<h2 style='color: #d91c84;'>ERP BM Make Up</h2>", unsafe_allow_html=True)
        st.markdown("<h3 style='font-size: 18px; margin-top: 5px; margin-bottom: 20px; color: #64748b;'>Acesso Restrito ao Sistema</h3>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                if usuario == "admin" and senha == "bmstore2026":
                    st.session_state.autenticado = True
                    st.query_params["auth"] = "true"
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# ==========================================
# FUNÇÕES DE BANCO DE DADOS
# ==========================================
def carregar_produtos():
    if not supabase:
        return pd.DataFrame(columns=["sku", "produto", "custo", "preco_venda", "taxa_ml", "frete_medio", "estoque"])
    try:
        response = supabase.table("produtos").select("*").execute()
        data = response.data
        if data: return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Aviso de conexão com o banco de produtos: {e}")
    return pd.DataFrame(columns=["sku", "produto", "custo", "preco_venda", "taxa_ml", "frete_medio", "estoque"])

def carregar_vendas():
    if not supabase:
        return pd.DataFrame(columns=["id", "data", "sku", "produto", "qtd", "pagamento", "preco_unit", "custo_unit", "taxa_ml", "frete"])
    try:
        response = supabase.table("vendas").select("*").execute()
        data = response.data
        if data:
            df = pd.DataFrame(data)
            if not df.empty and "data" in df.columns:
                df["data"] = pd.to_datetime(df["data"])
            return df
    except Exception as e:
        st.warning(f"Aviso de conexão com o banco de vendas: {e}")
    return pd.DataFrame(columns=["id", "data", "sku", "produto", "qtd", "pagamento", "preco_unit", "custo_unit", "taxa_ml", "frete"])

def render_tabela_saas(df, colunas):
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
    html_code = "<div style='background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); overflow: hidden; margin-top: 10px;'>"
    html_code += "<table style='width: 100%; border-collapse: collapse; font-family: \"Plus Jakarta Sans\", sans-serif; font-size: 14px; text-align: left;'><tr style='background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;'>"
    for col in colunas: html_code += f"<th style='padding: 14px 18px;'>{col}</th>"
    html_code += "</tr>"
    for idx, row in df.iterrows():
        bg_color = "#ffffff" if idx % 2 == 0 else "#fafafa"
        html_code += f"<tr style='background-color: {bg_color}; border-bottom: 1px solid #f1f5f9;'>"
        for col in colunas: html_code += f"<td style='padding: 14px 18px; color: #334155;'>{row[col] if col in row else ''}</td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    st.markdown(html_code, unsafe_allow_html=True)

# ==========================================
# BARRA LATERAL (MENU SAAS)
# ==========================================
st.sidebar.markdown("<h3 style='text-align: center; color: #d91c84; font-size: 18px; font-weight: 700; margin-top: 10px;'>ERP BM Make Up</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Navegação Principal</p>", unsafe_allow_html=True)

if 'menu_atual' not in st.session_state:
    st.session_state.menu_atual = "Dashboard Executivo"

if st.sidebar.button("📊  Dashboard Executivo", use_container_width=True): st.session_state.menu_atual = "Dashboard Executivo"; st.rerun()
if st.sidebar.button("📦  Gerenciar Produtos", use_container_width=True): st.session_state.menu_atual = "Cadastrar / Listar Produtos"; st.rerun()
if st.sidebar.button("🛒  Registrar Venda", use_container_width=True): st.session_state.menu_atual = "Registrar Venda"; st.rerun()
if st.sidebar.button("💡  Simulador de Lucro", use_container_width=True): st.session_state.menu_atual = "Simulador de Lucro por Venda"; st.rerun()
if st.sidebar.button("📋  Controle de Estoque", use_container_width=True): st.session_state.menu_atual = "Controle de Estoque"; st.rerun()

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Configurações</p>", unsafe_allow_html=True)
if st.sidebar.button("🔌 Integração Mercado Livre", use_container_width=True): st.session_state.menu_atual = "Integracao ML"; st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪  Sair / Logout", use_container_width=True):
    st.session_state.autenticado = False
    if "auth" in st.query_params: del st.query_params["auth"]
    st.rerun()

menu = st.session_state.menu_atual

def exibir_headline(titulo_pagina, subtitulo):
    col_logo, col_texto = st.columns([1, 8], vertical_alignment="center")
    with col_logo:
        if caminho_oficial_logo: st.image(caminho_oficial_logo, use_container_width=True)
    with col_texto:
        st.markdown("<span style='color: #d91c84; font-weight: bold; font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase;'>ERP BM MAKE UP STORE</span>", unsafe_allow_html=True)
        st.title(titulo_pagina)
        st.markdown(f"<p style='color: #64748b; font-size: 15px; margin-top: -5px;'>{subtitulo}</p>", unsafe_allow_html=True)
    st.markdown("---")

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

df_produtos = carregar_produtos()
df_vendas = carregar_vendas()

# ==========================================
# MÓDULOS DO SISTEMA
# ==========================================
if menu == "Dashboard Executivo":
    exibir_headline("Dashboard Executivo", "Desempenho financeiro, faturamento e lucratividade da loja em tempo real.")
    
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        filtro_periodo = st.selectbox("Selecione o Intervalo", ["Últimos 7 dias", "Últimos 14 dias", "Últimos 30 dias", "Personalizado"])
    
    hoje = datetime.now()
    if filtro_periodo == "Últimos 7 dias": data_inicio = hoje - timedelta(days=7)
    elif filtro_periodo == "Últimos 14 dias": data_inicio = hoje - timedelta(days=14)
    elif filtro_periodo == "Últimos 30 dias": data_inicio = hoje - timedelta(days=30)
    else:
        with col_f2:
            datas_pers = st.date_input("Selecione o Período", [hoje - timedelta(days=30), hoje])
            if len(datas_pers) == 2:
                data_inicio = datetime.combine(datas_pers[0], datetime.min.time())
                hoje = datetime.combine(datas_pers[1], datetime.max.time())
            else:
                data_inicio = hoje - timedelta(days=30)

    dias_delta = (hoje - data_inicio).days
    if dias_delta <= 0: dias_delta = 1
    
    data_fim_anterior = data_inicio - timedelta(seconds=1)
    data_inicio_anterior = data_fim_anterior - timedelta(days=dias_delta)

    if not df_vendas.empty:
        df_atual = df_vendas[(df_vendas["data"] >= data_inicio) & (df_vendas["data"] <= hoje)]
        df_ant = df_vendas[(df_vendas["data"] >= data_inicio_anterior) & (df_vendas["data"] <= data_fim_anterior)]
    else:
        df_atual = pd.DataFrame(columns=["data", "sku", "qtd", "pagamento", "preco_unit", "custo_unit", "taxa_ml", "frete"])
        df_ant = pd.DataFrame(columns=["data", "sku", "qtd", "pagamento", "preco_unit", "custo_unit", "taxa_ml", "frete"])

    fat_atual = (df_atual["qtd"] * df_atual["preco_unit"]).sum() if not df_atual.empty else 0.0
    custos_atual = ((df_atual["qtd"] * df_atual["custo_unit"]) + (df_atual["qtd"] * df_atual["taxa_ml"]) + (df_atual["qtd"] * df_atual["frete"])).sum() if not df_atual.empty else 0.0
    lucro_atual = fat_atual - custos_atual
    margem_atual = (lucro_atual / fat_atual * 100) if fat_atual > 0 else 0.0
    vendas_atual = df_atual['qtd'].sum() if not df_atual.empty else 0
    skus_atual = len(df_produtos)

    fat_ant = (df_ant["qtd"] * df_ant["preco_unit"]).sum() if not df_ant.empty else 0.0
    custos_ant = ((df_ant["qtd"] * df_ant["custo_unit"]) + (df_ant["qtd"] * df_ant["taxa_ml"]) + (df_ant["qtd"] * df_ant["frete"])).sum() if not df_ant.empty else 0.0
    lucro_ant = fat_ant - custos_ant
    margem_ant = (lucro_ant / fat_ant * 100) if fat_ant > 0 else 0.0
    vendas_ant = df_ant['qtd'].sum() if not df_ant.empty else 0

    def calc_delta(atual, anterior):
        if anterior == 0: return f"{100.0:.1f}%" if atual > 0 else "0.0%"
        var = ((atual - anterior) / anterior) * 100
        return f"{var:.1f}%"

    st.markdown("<br>", unsafe_allow_html=True)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Faturamento Total", formatar_moeda(fat_atual), calc_delta(fat_atual, fat_ant))
    k2.metric("Lucro Total", formatar_moeda(lucro_atual), calc_delta(lucro_atual, lucro_ant))
    k3.metric("Margem de Lucro Média", f"{margem_atual:.1f}%", calc_delta(margem_atual, margem_ant))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    k4, k5, k6 = st.columns(3)
    k4.metric("Total de Custos", formatar_moeda(custos_atual), calc_delta(custos_atual, custos_ant), delta_color="inverse")
    k5.metric("Volume de Vendas", f"{vendas_atual} un", calc_delta(vendas_atual, vendas_ant))
    k6.metric("Total de SKUs Ativos", f"{skus_atual}", "0.0%", delta_color="off")

    st.markdown("<br>---<br>", unsafe_allow_html=True)
    st.subheader("📋 Histórico de Vendas no Período")
    if not df_atual.empty:
        df_exibicao = df_atual.copy()
        df_exibicao["Data"] = df_exibicao["data"].dt.strftime('%d/%m/%Y')
        df_exibicao["Faturamento"] = (df_exibicao["qtd"] * df_exibicao["preco_unit"]).apply(formatar_moeda)
        df_exibicao["Lucro Líquido"] = ((df_exibicao["qtd"] * df_exibicao["preco_unit"]) - ((df_exibicao["qtd"] * df_exibicao["custo_unit"]) + (df_exibicao["qtd"] * df_exibicao["taxa_ml"]) + (df_exibicao["qtd"] * df_exibicao["frete"]))).apply(formatar_moeda)
        
        render_tabela_saas(df_exibicao, ["Data", "produto", "qtd", "pagamento", "Faturamento", "Lucro Líquido"])
    else:
        st.info("Nenhuma venda registrada neste período.")

elif menu == "Cadastrar / Listar Produtos":
    exibir_headline("Gerenciamento de Produtos", "Cadastre novos itens salvos diretamente na nuvem.")
    
    with st.expander("➕ Expandir Formulário para Novo Produto", expanded=True):
        with st.form("form_produto"):
            col1, col2, col3 = st.columns(3)
            with col1:
                sku = st.text_input("SKU / Código do Produto")
                nome = st.text_input("Nome do Produto")
            with col2:
                custo = st.number_input("Preço de Custo (R$)", min_value=0.0, format="%.2f")
                preco_venda = st.number_input("Preço de Venda Padrão (R$)", min_value=0.0, format="%.2f")
            with col3:
                taxa_ml = st.number_input("Taxa Média do ML (%)", value=16.0, min_value=0.0)
                frete_medio = st.number_input("Custo Fixo / Frete (R$)", value=0.0, min_value=0.0)
                estoque = st.number_input("Estoque Inicial", min_value=0, value=10, step=1)
                
            if st.form_submit_button("Salvar Novo Produto") and sku and nome:
                novo_produto = {
                    "sku": sku, "produto": nome, "custo": custo, 
                    "preco_venda": preco_venda, "taxa_ml": taxa_ml, 
                    "frete_medio": frete_medio, "estoque": estoque
                }
                try:
                    supabase.table("produtos").insert(novo_produto).execute()
                    st.success(f"Produto '{nome}' salvo no banco de dados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar produto: {e}")

    st.subheader("Catálogo de Produtos")
    if not df_produtos.empty:
        render_tabela_saas(df_produtos, ["sku", "produto", "custo", "preco_venda", "taxa_ml", "frete_medio", "estoque"])
        
        with st.expander("🗑️ Excluir Produto por SKU"):
            sku_para_excluir = st.selectbox("Selecione o SKU para remover", df_produtos["sku"].tolist())
            if st.button("Excluir Produto Permanentemente"):
                try:
                    supabase.table("produtos").delete().eq("sku", sku_para_excluir).execute()
                    st.success("Produto excluído com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
    else:
        st.info("Nenhum produto cadastrado.")

elif menu == "Registrar Venda":
    exibir_headline("Registrar Nova Venda", "Lançamentos com preço customizável salvos permanentemente na nuvem.")
    
    if df_produtos.empty:
        st.warning("Cadastre produtos primeiro na aba de Gerenciamento.")
    else:
        with st.expander("🛒 Nova Venda", expanded=True):
            prod_vendido = st.selectbox("Escolha o Produto", df_produtos["produto"].tolist())
            p_info = df_produtos[df_produtos["produto"] == prod_vendido].iloc[0]
            preco_sugerido = float(p_info["preco_venda"])
            
            with st.form("form_venda"):
                col1, col2 = st.columns(2)
                with col1:
                    qtd_vendida = st.number_input("Quantidade Vendida", min_value=1, value=1, step=1)
                    preco_unit_custom = st.number_input("Preço Unitário de Venda (R$)", value=preco_sugerido, min_value=0.0, format="%.2f")
                with col2:
                    data_venda = st.date_input("Data da Venda", datetime.now())
                    forma_pgto = st.selectbox("Forma de Pagamento", ["Mercado Livre", "PIX", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Outro"])
                
                if st.form_submit_button("Confirmar e Registrar Venda"):
                    nova_venda = {
                        "data": datetime.combine(data_venda, datetime.min.time()).isoformat(),
                        "sku": p_info["sku"],
                        "produto": prod_vendido,
                        "qtd": int(qtd_vendida),
                        "pagamento": forma_pgto,
                        "preco_unit": float(preco_unit_custom),
                        "custo_unit": float(p_info["custo"]),
                        "taxa_ml": float(preco_unit_custom * (p_info["taxa_ml"] / 100)) if forma_pgto == "Mercado Livre" else 0.0,
                        "frete": float(p_info["frete_medio"]) if forma_pgto == "Mercado Livre" else 0.0
                    }
                    
                    try:
                        supabase.table("vendas").insert(nova_venda).execute()
                        novo_estoque = int(p_info["estoque"]) - int(qtd_vendida)
                        supabase.table("produtos").update({"estoque": novo_estoque}).eq("sku", p_info["sku"]).execute()
                        st.success("Venda registrada com preço customizado e estoque atualizado na nuvem!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao registrar venda: {e}")

    st.subheader("Histórico Geral de Vendas")
    if not df_vendas.empty:
        df_exibicao_geral = df_vendas.copy()
        if "data" in df_exibicao_geral.columns:
            df_exibicao_geral["Data"] = df_exibicao_geral["data"].dt.strftime('%d/%m/%Y')
        render_tabela_saas(df_exibicao_geral, ["id", "Data", "produto", "qtd", "pagamento", "preco_unit"])
        
        with st.expander("🗑️ Excluir Venda por ID"):
            id_para_excluir = st.number_input("Digite o ID da venda que deseja apagar", min_value=1, step=1)
            if st.button("Excluir Venda"):
                try:
                    supabase.table("vendas").delete().eq("id", id_para_excluir).execute()
                    st.success("Venda removida do histórico!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
    else:
        st.info("O histórico de vendas está vazio.")

elif menu == "Simulador de Lucro por Venda":
    exibir_headline("Simulador de Lucro Real", "Análise detalhada descontando comissões do marketplace, frete e custos.")
    
    if df_produtos.empty:
        st.warning("Cadastre produtos primeiro.")
    else:
        produto_selecionado = st.selectbox("Selecione o Produto", df_produtos["produto"].tolist())
        prod_data = df_produtos[df_produtos["produto"] == produto_selecionado].iloc[0]
        
        preco = float(prod_data["preco_venda"])
        custo = float(prod_data["custo"])
        taxa_ml_pct = float(prod_data["taxa_ml"]) / 100
        frete = float(prod_data["frete_medio"])
        
        valor_taxa_ml = preco * taxa_ml_pct
        lucro_bruto = preco - custo - valor_taxa_ml - frete
        margem_lucro = (lucro_bruto / preco * 100) if preco > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Preço de Venda", formatar_moeda(preco))
        col2.metric("Custo de Aquisição", formatar_moeda(custo))
        col3.metric("Taxa ML + Frete", formatar_moeda(valor_taxa_ml + frete))
        col4.metric("Lucro Líquido Real", formatar_moeda(lucro_bruto), f"{margem_lucro:.1f}%")
        
        if margem_lucro < 10:
            st.error("⚠️ Atenção: Sua margem de lucro está abaixo de 10%!")
        elif margem_lucro >= 20:
            st.success("✅ Margem de lucro saudável e dentro do planejado!")

elif menu == "Controle de Estoque":
    exibir_headline("Gestão de Estoque", "Acompanhe o saldo físico dos produtos na nuvem.")
    if not df_produtos.empty:
        render_tabela_saas(df_produtos, ["sku", "produto", "estoque", "preco_venda", "custo"])
        baixo_estoque = df_produtos[df_produtos["estoque"] <= 3]
        if not baixo_estoque.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("⚠️ Alerta: Produtos com estoque crítico:")
            render_tabela_saas(baixo_estoque, ["sku", "produto", "estoque"])
    else:
        st.info("Estoque vazio.")

# -------------------------------------------------------------
# ABA: INTEGRAÇÃO MERCADO LIVRE (RESOLUÇÃO VIA IP DO GOOGLE DNS)
# -------------------------------------------------------------
elif menu == "Integracao ML":
    st.title("Integração Oficial - Mercado Livre")
    
    ML_APP_ID = obter_segredo("ML_APP_ID")
    ML_CLIENT_SECRET = obter_segredo("ML_CLIENT_SECRET")
    ML_REDIRECT_URI = obter_segredo("ML_REDIRECT_URI")

    if not ML_APP_ID or not ML_CLIENT_SECRET:
        st.error("Erro: As chaves do Mercado Livre não foram configuradas nas variáveis de ambiente.")
        st.stop()

    query_params = st.query_params
    auth_code = query_params.get("code")

    try:
        tokens_data = supabase.table("ml_tokens").select("*").execute().data
        is_connected = len(tokens_data) > 0
    except Exception:
        is_connected = False

    if auth_code and not is_connected:
        with st.spinner("A estabelecer ligação segura com o Mercado Livre..."):
            try:
                # Resolve o IP utilizando diretamente o IP do Google DNS (8.8.8.8) para evitar o bloqueio de DNS do Render
                target_ip = "api.mercadolivre.com"
                try:
                    dns_res = requests.get(
                        "https://8.8.8.8/resolve",
                        params={"name": "api.mercadolivre.com", "type": "A"},
                        timeout=5,
                        verify=False
                    )
                    if dns_res.status_code == 200:
                        dns_data = dns_res.json()
                        for record in dns_data.get("Answer", []):
                            if record.get("type") == 1:
                                target_ip = record.get("data")
                                break
                except Exception:
                    pass

                token_url = f"https://{target_ip}/oauth/token"
                
                payload = {
                    "grant_type": "authorization_code",
                    "client_id": ML_APP_ID,
                    "client_secret": ML_CLIENT_SECRET,
                    "code": auth_code,
                    "redirect_uri": ML_REDIRECT_URI
                }
                
                headers = {
                    "accept": "application/json",
                    "content-type": "application/x-www-form-urlencoded",
                    "Host": "api.mercadolivre.com"
                }
                
                # verify=False é obrigatório ao saltar a resolução DNS e ligar diretamente por IP com Host header
                response = requests.post(token_url, data=payload, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
                    
                    if access_token:
                        supabase.table("ml_tokens").upsert({
                            "id": 1, 
                            "access_token": access_token, 
                            "refresh_token": refresh_token
                        }).execute()
                        
                        st.query_params.clear()
                        st.success("✅ Ligação estabelecida com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Resposta inválida: {token_data}")
                else:
                    st.error(f"Erro na autorização (Estado {response.status_code}): {response.text}")
            except Exception as e:
                st.error(f"Erro de comunicação: {e}")

    if is_connected:
        st.success("✅ STATUS: Conectado ao Mercado Livre com Sucesso!")
        access_token = tokens_data[0]["access_token"]
        
        st.markdown("---")
        st.subheader("🔄 Sincronização de Catálogo e Financeiro")
        st.write("O ERP atua como espelho do Mercado Livre. O estoque e financeiro são baseados na plataforma.")

        col_sync1, col_sync2 = st.columns(2)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. ESPELHAMENTO DE PRODUTOS E ESTOQUE
        with col_sync1:
            if st.button("📦 Puxar Estoque Atualizado (ML)", use_container_width=True):
                with st.spinner("Lendo catálogo do Mercado Livre..."):
                    user_resp = requests.get("https://api.mercadolivre.com/users/me", headers=headers, verify=False)
                    if user_resp.status_code == 200:
                        user_id = user_resp.json().get("id")
                        items_resp = requests.get(f"https://api.mercadolivre.com/users/{user_id}/items/search", headers=headers, verify=False)
                        
                        if items_resp.status_code == 200:
                            item_ids = items_resp.json().get("results", [])
                            produtos_salvos = 0
                            
                            for item_id in item_ids:
                                detail_resp = requests.get(f"https://api.mercadolivre.com/items/{item_id}", headers=headers, verify=False)
                                if detail_resp.status_code == 200:
                                    prod = detail_resp.json()
                                    sku_val = prod.get("seller_custom_field")
                                    if not sku_val:
                                        for attr in prod.get("attributes", []):
                                            if attr.get("id") == "SELLER_SKU":
                                                sku_val = attr.get("value_name")
                                                break
                                    if not sku_val:
                                        sku_val = str(prod.get("id"))
                                    
                                    payload_prod = {
                                        "sku": str(sku_val),
                                        "produto": str(prod.get("title", "")),
                                        "preco_venda": float(prod.get("price", 0.0)),
                                        "estoque": int(prod.get("available_quantity", 0))
                                    }
                                    try:
                                        supabase.table("produtos").upsert(payload_prod, on_conflict="sku").execute()
                                        produtos_salvos += 1
                                    except Exception as err:
                                        st.error(f"Erro ao salvar produto {sku_val}: {err}")
                            st.success(f"Catálogo espelhado! {produtos_salvos} produtos atualizados.")
                        else:
                            st.error(f"Erro ao buscar catálogo: {items_resp.text}")
                    else:
                        st.error("Erro de usuário. Token pode estar inválido.")

        # 2. REGISTRO DE VENDAS
        with col_sync2:
            if st.button("🛒 Puxar Vendas e Taxas (ML)", use_container_width=True):
                with st.spinner("Processando financeiro item a item..."):
                    user_resp = requests.get("https://api.mercadolivre.com/users/me", headers=headers, verify=False)
                    if user_resp.status_code == 200:
                        user_id = user_resp.json().get("id")
                        orders_resp = requests.get(f"https://api.mercadolivre.com/orders/search?seller={user_id}", headers=headers, verify=False)
                        
                        if orders_resp.status_code == 200:
                            orders_list = orders_resp.json().get("results", [])
                            itens_salvos = 0
                            
                            for order in orders_list:
                                order_id = str(order.get("id"))
                                data_venda = str(order.get("date_closed") or order.get("date_created", ""))
                                custo_frete = 0.0
                                metodo_pagamento = str(order.get("status", "pago"))
                                payments = order.get("payments", [])
                                if payments:
                                    custo_frete = float(payments[0].get("shipping_cost", 0.0))
                                    metodo_pagamento = str(payments[0].get("payment_method_id", metodo_pagamento))
                                
                                order_items = order.get("order_items", [])
                                for idx, item in enumerate(order_items):
                                    item_bd_id = f"{order_id}-{idx}" if len(order_items) > 1 else order_id
                                    sku_item = item.get("item", {}).get("seller_sku")
                                    if not sku_item:
                                        sku_item = str(item.get("item", {}).get("id", ""))
                                    produto_nome = str(item.get("item", {}).get("title", ""))
                                    preco_unit = float(item.get("unit_price", 0.0))
                                    quantidade = int(item.get("quantity", 1))
                                    taxa_ml = float(item.get("sale_fee", 0.0))
                                    
                                    payload_venda = {
                                        "id": item_bd_id,
                                        "data": data_venda,
                                        "sku": sku_item,
                                        "produto": produto_nome,
                                        "pagamento": metodo_pagamento,
                                        "preco_unit": preco_unit,
                                        "custo_unit": 0.0,
                                        "taxa_ml": taxa_ml,
                                        "frete": custo_frete,
                                        "quantidade": quantidade
                                    }
                                    try:
                                        supabase.table("vendas").upsert(payload_venda, on_conflict="id").execute()
                                        itens_salvos += 1
                                    except Exception as err:
                                        st.error(f"Erro ao salvar item {sku_item}: {err}")
                            st.success(f"Financeiro sincronizado! {itens_salvos} itens registrados.")
                        else:
                            st.error(f"Erro ao buscar histórico: {orders_resp.text}")
                    else:
                        st.error("Erro de usuário. Token pode estar inválido.")
                        
        st.markdown("---")
        if st.button("Desconectar Conta (Sair)"):
            supabase.table("ml_tokens").delete().eq("id", 1).execute()
            st.query_params.clear()
            st.rerun()

    else:
        st.warning("⚠️ O ERP não está conectado ao Mercado Livre.")
        st.write("Por favor, clique no botão abaixo para autorizar o aplicativo:")
        
        auth_url = f"https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={ML_APP_ID}&redirect_uri={ML_REDIRECT_URI}"
        
        st.markdown(
            f"""
            <div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
                <a href="{auth_url}" target="_self" style="background-color: #ffe600; color: #333333; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; box-shadow: 0px 2px 5px rgba(0,0,0,0.1);">
                    🔗 Conectar ao Mercado Livre
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
