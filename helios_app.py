import streamlit as st
import os
import sys
import subprocess

# --- HACK DE AUTO-REPARO (Força instalação do gTTS) ---
try:
    from gTTS import gTTS
except ImportError:
    # Se der erro de "Não encontrado", o Helios instala sozinho agora
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gTTS"])
    from gTTS import gTTS

from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io

# --- CONFIGURAÇÃO VISUAL TRON ---
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    
    /* Inputs */
    .stTextInput > div > div > input { 
        background-color: #0a0a0a; color: #FFD700; border: 1px solid #FFD700; 
        font-family: 'Share Tech Mono', monospace; 
    }
    
    /* Botões */
    .stButton > button { 
        background-color: #000000; color: #FFD700; border: 2px solid #FFD700; 
        border-radius: 0px; text-transform: uppercase; transition: 0.3s; width: 100%;
    }
    .stButton > button:hover { 
        background-color: #FFD700; color: #000000; box-shadow: 0 0 15px #FFD700; 
    }
    
    /* Texto */
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    header {visibility: hidden;}
    
    /* Caixa de Resposta */
    .helios-box {
        border: 1px solid #FFD700; 
        padding: 20px; 
        background-color: #050505; 
        border-left: 5px solid #FFD700;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 10])
with col1: st.title("🟡")
with col2: st.title("HELIOS // SYSTEM v3.1")

st.markdown("`[STATUS: PROTOCOLO DE AUTO-REPARO ATIVO]`")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header(">> CONFIGURAÇÃO")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    voz_ativa = st.toggle("RESPOSTA DE VOZ (HELIOS)", value=True)
    st.info("DOMÍNIO: HELIOS.IA.BR")

# --- LÓGICA ---
if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

SYSTEM_INSTRUCTION = """
INSTRUÇÃO DE SISTEMA: Você é o HELIOS.
Fale Português do Brasil. Seja técnico, conciso e útil.
Use [STATUS], >>. Não use emojis.
"""

def falar_resposta(texto):
    """Gera áudio da resposta"""
    if voz_ativa:
        try:
            tts = gTTS(text=texto, lang='pt', slow=False)
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            st.audio(audio_bytes, format='audio/mp3', start_time=0)
        except Exception as e:
            st.warning(f"[FALHA NO AUDIO]: {e}")

def processar(texto_usuario=None, imagem_usuario=None, audio_usuario=None):
    lista_partes = []
    
    prompt_base = SYSTEM_INSTRUCTION
    
    if texto_usuario:
        prompt_base += f"\n\nUSUÁRIO (TEXTO): {texto_usuario}"
    
    lista_partes.append(Part(text=prompt_base))
    
    if imagem_usuario:
        img = Image.open(imagem_usuario)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        lista_partes.append(Part(inline_data={"mime_type": "image/jpeg", "data": buf.getvalue()}))
        
    if audio_usuario:
        audio_bytes = audio_usuario.getvalue()
        lista_partes.append(Part(inline_data={"mime_type": "audio/wav", "data": audio_bytes}))

    if not texto_usuario and not imagem_usuario and not audio_usuario:
        return

    with st.spinner(">> PROCESSANDO DADOS NEURAIS..."):
        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=[Content(role="user", parts=lista_partes)]
            )
            
            resposta_final = response.text
            
            st.markdown(f"""
            <div class="helios-box">
            <strong style="color: #FFD700;">>> HELIOS RESPOSTA:</strong><br><br>
            <span style="color: #FFF;">{resposta_final}</span>
            </div>
            """, unsafe_allow_html=True)
            
            falar_resposta(resposta_final)
                
        except Exception as e:
            st.error(f">> ERRO DE COMUNICAÇÃO: {e}")

# --- INTERFACE PRINCIPAL ---

col_text, col_cam = st.columns(2)

with col_text:
    st.subheader(">> COMANDO DE VOZ / TEXTO")
    
    audio_rec = st.audio_input("GRAVAR COMANDO DE VOZ")
    if audio_rec:
        st.write(">> ÁUDIO CAPTURADO")
        processar(audio_usuario=audio_rec)
        
    st.markdown("--- OU ---")
    
    with st.form("form_txt"):
        txt = st.text_input("DIGITAR COMANDO:")
        if st.form_submit_button("ENVIAR TEXTO"):
            processar(texto_usuario=txt)

with col_cam:
    st.subheader(">> SENSOR VISUAL")
    cam = st.camera_input("ATIVAR CÂMERA")
    if cam:
        if st.button("ANALISAR IMAGEM"):
            processar(imagem_usuario=cam, texto_usuario="Descreva o que vê.")
