import streamlit as st
import os
from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io

# --- CONFIGURAÇÃO DA PÁGINA (VISUAL TRON) ---
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

# CSS: O Estilo "Filme Antigo / TRON"
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

    .stApp {
        background-color: #000000;
        color: #FFD700;
        font-family: 'Share Tech Mono', monospace;
    }
    
    .stTextInput > div > div > input {
        background-color: #0a0a0a;
        color: #FFD700;
        border: 1px solid #FFD700;
        font-family: 'Share Tech Mono', monospace;
    }
    
    .stButton > button {
        background-color: #000000;
        color: #FFD700;
        border: 2px solid #FFD700;
        border-radius: 0px;
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #FFD700;
        color: #000000;
        box-shadow: 0 0 15px #FFD700;
        border-color: #FFD700;
    }
    
    h1, h2, h3, p, label, span, div {
        color: #FFD700 !important;
        font-family: 'Share Tech Mono', monospace !important;
        text-shadow: 0 0 2px #b8860b;
    }
    
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("# 🟡")
with col_title:
    st.title("HELIOS // INTERFACE v1.0")
    st.markdown("`[STATUS: AGUARDANDO CREDENCIAIS]`")

st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header(">> CONFIGURAÇÃO")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    st.markdown("---")
    st.info("SISTEMA ONLINE\nDOMÍNIO: HELIOS.IA.BR")

# --- LÓGICA DO CÉREBRO ---
if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO NA BARRA LATERAL PARA INICIAR.")
    st.stop()

# Configura o cliente Gemini
try:
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
except Exception as e:
    st.error(f"ERRO DE CONEXÃO: {e}")
    st.stop()

MODELO = "gemini-2.0-flash-exp"

SYSTEM_PROMPT = """
Você é o HELIOS, uma IA avançada com interface TRON.
Fale Português do Brasil. Seja conciso, técnico e direto.
Não use emojis. Use [STATUS], >>, //.
Se receber imagem, descreva analiticamente.
"""

def falar(texto):
    """Modo Silencioso: Função desativada temporariamente"""
    pass

def processar(prompt_texto, imagem_arquivo=None):
    """Envia para o Gemini"""
    conteudo = []
    
    if prompt_texto:
        conteudo.append(Part.from_text(prompt_texto))
    
    if imagem_arquivo:
        img = Image.open(imagem_arquivo)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        conteudo.append(Part.from_bytes(buf.getvalue(), "image/jpeg"))

    if not conteudo:
        return

    with st.spinner(">> PROCESSANDO DADOS NEURAIS..."):
        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=[
                    Content(role="system", parts=[Part.from_text(SYSTEM_PROMPT)]),
                    Content(role="user", parts=conteudo)
                ]
            )
            
            resposta = response.text
            
            st.markdown(f"""
            <div style="border: 1px solid #FFD700; padding: 10px; background-color: #111;">
            <strong>>> HELIOS RESPOSTA:</strong><br><br>{resposta}
            </div>
            """, unsafe_allow_html=True)
            
            # Tenta falar (vai ignorar pois está no modo silencioso)
            falar(resposta)
                
        except Exception as e:
            st.error(f">> ERRO CRÍTICO: {e}")

# --- ÁREA PRINCIPAL ---
col1, col2 = st.columns(2)

with col1:
    st.subheader(">> ENTRADA DE TEXTO")
    texto = st.text_input("COMANDO:", key="cmd_input")
    if st.button("ENVIAR DADOS [ENTER]"):
        processar(texto)

with col2:
    st.subheader(">> ENTRADA VISUAL")
    imagem = st.camera_input("SENSOR ÓPTICO")
    
    if imagem:
        st.write(">> IMAGEM CAPTURADA NO BUFFER")
        if st.button("ANALISAR VISUAL"):
            prompt_visual = texto if texto else "Descreva o que os sensores visuais captaram."
            processar(prompt_visual, imagem)
