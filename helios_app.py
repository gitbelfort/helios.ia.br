import streamlit as st
import os
from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

# CSS TRON / TERMINAL
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    .stTextInput > div > div > input { background-color: #0a0a0a; color: #FFD700; border: 1px solid #FFD700; font-family: 'Share Tech Mono', monospace; }
    .stButton > button { background-color: #000000; color: #FFD700; border: 2px solid #FFD700; border-radius: 0px; text-transform: uppercase; transition: 0.3s; }
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 15px #FFD700; }
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col_logo, col_title = st.columns([1, 5])
with col_logo: st.markdown("# 🟡")
with col_title:
    st.title("HELIOS // INTERFACE v2.1")
    st.markdown("`[STATUS: AGUARDANDO COMANDO]`")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header(">> CONFIGURAÇÃO")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    st.info("DOMÍNIO: HELIOS.IA.BR")

# --- LÓGICA ---
if not api_key:
    st.warning(">> INSIRA A CHAVE NA BARRA LATERAL.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

# Prompt embutido (Cavalo de Tróia)
SYSTEM_INSTRUCTION = """
INSTRUÇÃO MESTRA: Você é o HELIOS, IA com interface TRON.
Fale Português do Brasil. Seja técnico, conciso e útil.
Use [STATUS], >>. Não use emojis.
Se receber imagem, descreva analiticamente.
"""

def processar(prompt_texto, imagem_arquivo=None):
    lista_partes = []
    
    # 1. Injeta a personalidade HELIOS como se fosse texto do usuário
    # Isso evita o erro "System role not supported"
    texto_final = SYSTEM_INSTRUCTION + "\n\n" + "USUÁRIO DIZ: " + (prompt_texto if prompt_texto else "Analise a entrada visual.")
    
    lista_partes.append(Part(text=texto_final))
    
    if imagem_arquivo:
        img = Image.open(imagem_arquivo)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        lista_partes.append(Part(inline_data={"mime_type": "image/jpeg", "data": buf.getvalue()}))

    with st.spinner(">> PROCESSANDO DADOS..."):
        try:
            # Enviamos tudo como "user", o Gemini é esperto e entende a instrução.
            response = client.models.generate_content(
                model=MODELO,
                contents=[
                    Content(role="user", parts=lista_partes)
                ]
            )
            
            resposta = response.text
            
            st.markdown(f"""
            <div style="border: 1px solid #FFD700; padding: 15px; background-color: #050505; border-left: 5px solid #FFD700;">
            <strong style="color: #FFD700;">>> HELIOS RESPOSTA:</strong><br><br>
            <span style="color: #FFF;">{resposta}</span>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f">> ERRO: {e}")

# --- INTERFACE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader(">> ENTRADA DE TEXTO")
    with st.form("texto_form"):
        txt = st.text_input("COMANDO:")
        if st.form_submit_button("ENVIAR"):
            processar(txt)

with col2:
    st.subheader(">> ENTRADA VISUAL")
    cam = st.camera_input("SENSOR ÓPTICO")
    if cam and st.button("ANALISAR VISUAL"):
        processar(txt if txt else "", cam)
