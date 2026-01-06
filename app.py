import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Monitor de Saúde", layout="wide")

# --- Conexão com Banco de Dados (SQLite) ---
def init_db():
    conn = sqlite3.connect('dados_saude.db')
    c = conn.cursor()
    # Tabela para histórico de peso
    c.execute('''CREATE TABLE IF NOT EXISTS historico_peso
                 (data TEXT, peso REAL)''')
    conn.commit()
    return conn

conn = init_db()

# --- Funções de Banco de Dados ---
def salvar_peso(peso_atual):
    c = conn.cursor()
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    # Verifica se já tem registro hoje para não duplicar
    c.execute("SELECT * FROM historico_peso WHERE data = ?", (data_hoje,))
    if c.fetchone():
        c.execute("UPDATE historico_peso SET peso = ? WHERE data = ?", (peso_atual, data_hoje))
    else:
        c.execute("INSERT INTO historico_peso (data, peso) VALUES (?, ?)", (data_hoje, peso_atual))
    conn.commit()

def carregar_historico():
    return pd.read_sql("SELECT * FROM historico_peso ORDER BY data ASC", conn)

# --- Estilo CSS (Design Minimalista) ---
st.markdown("""
    <style>
    /* Remove preenchimento padrão excessivo */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Estilo dos Cards/Métricas */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Títulos mais sóbrios */
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 600; color: #333; }
    
    /* Botões */
    .stButton>button {
        background-color: #333;
        color: white;
        border: none;
        border-radius: 6px;
        height: 3rem;
    }
    .stButton>button:hover {
        background-color: #555;
        color: white;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Inicialização de Variáveis de Sessão ---
if 'calorias_consumidas' not in st.session_state:
    st.session_state.calorias_consumidas = 0

# --- Barra Lateral (Configurações e Entrada de Dados) ---
with st.sidebar:
    st.header("Configurações do Usuário")
    
    # Dados biométricos
    genero = st.selectbox("Gênero", ["Masculino", "Feminino"])
    idade = st.number_input("Idade", value=25)
    altura = st.number_input("Altura (cm)", value=175)
    
    st.divider()
    
    st.subheader("Atualizar Peso")
    # Input de peso que salva no banco
    peso_input = st.number_input("Peso Atual (kg)", value=70.0, step=0.1)
    if st.button("Salvar Peso Hoje"):
        salvar_peso(peso_input)
        st.success("Peso registrado com sucesso.")
    
    st.divider()
    
    nivel_atividade = st.selectbox("Nível de Atividade", 
        ["Sedentário", "Levemente ativo", "Moderadamente ativo", "Muito ativo"])
    
    objetivo = st.selectbox("Objetivo", 
        ["Perder Gordura", "Manter Peso", "Ganhar Massa"])

# --- Lógica de Cálculos ---
# Carregar histórico para usar o peso mais recente no cálculo
df_historico = carregar_historico()

if not df_historico.empty:
    peso_atual = df_historico.iloc[-1]['peso']
else:
    peso_atual = peso_input # Usa o do input se não tiver histórico

# IMC
altura_m = altura / 100
imc = peso_atual / (altura_m ** 2)

# TMB
if genero == "Masculino":
    tmb = 88.36 + (13.4 * peso_atual) + (4.8 * altura) - (5.7 * idade)
else:
    tmb = 447.6 + (9.2 * peso_atual) + (3.1 * altura) - (4.3 * idade)

# TDEE (Gasto Total)
fatores = {"Sedentário": 1.2, "Levemente ativo": 1.375, "Moderadamente ativo": 1.55, "Muito ativo": 1.725}
tdee = tmb * fatores[nivel_atividade]

# Meta Calórica
if objetivo == "Perder Gordura": meta = tdee - 500
elif objetivo == "Ganhar Massa": meta = tdee + 400
else: meta = tdee

# --- Interface Principal ---
st.title("Painel de Controle Corporal")
st.write(f"Resumo diário para **{datetime.now().strftime('%d/%m/%Y')}**")

# Layout em colunas para Métricas
col1, col2, col3, col4 = st.columns(4)
col1.metric("Peso Atual", f"{peso_atual} kg")
col2.metric("IMC", f"{imc:.1f}")
col3.metric("Meta Calórica", f"{int(meta)} kcal")
col4.metric("Consumido Hoje", f"{st.session_state.calorias_consumidas} kcal")

st.divider()

# --- Seção: Acompanhamento de Evolução (Gráfico) ---
st.subheader("Evolução de Peso")

if not df_historico.empty:
    # Conversão de data para datetime para o gráfico entender
    df_historico['data'] = pd.to_datetime(df_historico['data'])
    
    # Criar gráfico de linha limpo
    st.line_chart(df_historico, x='data', y='peso', color='#333333')
    
    # Mostrar tabela se quiser ver os detalhes (em um expander para não poluir)
    with st.expander("Ver histórico detalhado em tabela"):
        st.dataframe(df_historico.sort_values(by='data', ascending=False), use_container_width=True)
else:
    st.info("Salve seu peso na barra lateral para começar a ver o gráfico de evolução.")

st.divider()

# --- Seção: Calculadora Rápida de Calorias do Dia ---
# Layout de duas colunas: Esquerda (Input), Direita (Barra de Progresso)
c_left, c_right = st.columns([1, 2])

with c_left:
    st.subheader("Adicionar Refeição")
    with st.form("add_calorias"):
        kcal_input = st.number_input("Calorias (kcal)", min_value=0, step=10)
        submit = st.form_submit_button("Registrar")
        if submit:
            st.session_state.calorias_consumidas += kcal_input
            st.rerun()

with c_right:
    st.subheader("Progresso da Dieta")
    progresso = min(st.session_state.calorias_consumidas / meta, 1.0)
    st.progress(progresso)
    
    restante = int(meta - st.session_state.calorias_consumidas)
    if restante > 0:
        st.caption(f"Faltam **{restante} kcal** para atingir sua meta.")
    else:
        st.caption(f"Você ultrapassou a meta em **{abs(restante)} kcal**.")
    
    # Botão resetar dia
    if st.button("Reiniciar contagem do dia"):
        st.session_state.calorias_consumidas = 0
        st.rerun()
