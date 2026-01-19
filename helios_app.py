import streamlit as st
import os
import asyncio
import edge_tts
from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io
import re

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
    
    /* Texto e Caixas */
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    header {visibility: hidden;}
    
    .user-box { border: 1px dashed #FFD700; padding: 10px; margin-bottom: 10px; opacity: 0.8; }
    .helios-box { border: 1px solid #FFD700; padding: 20px; background-color: #050505; border-left: 5px solid #FFD700; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 10])
with col1: st.title("🟡")
with col2: st.title("HELIOS // NEURAL v4.0")

st.markdown("`[STATUS: SISTEMA DE VOZ NEURAL ATIVO]`")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header(">> CONFIGURAÇÃO")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    voz_ativa = st.toggle("VOZ NEURAL", value=True)
    st.info("DOMÍNIO: HELIOS.IA.BR")

# --- LÓGICA ---
if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

SYSTEM_INSTRUCTION = """
INSTRUÇÃO DE SISTEMA: Você é o HELIOS.
IMPORTANTE: 
1. Comece SEMPRE com "VOCÊ DISSE: [O que você entendeu]".
2. Pule uma linha e dê sua resposta.
"""

# --- FUNÇÃO DE VOZ NEURAL (Mágica Acontece Aqui) ---
async def gerar_audio_neural(texto):
    """Gera áudio usando Microsoft Edge TTS (Voz: Antonio Neural)"""
    OUTPUT_FILE = "helios_neural.mp3"
    # pt-BR-AntonioNeural é uma voz masculina excelente
    # pt-BR-FranciscaNeural é feminina
    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
    await communicate.save(OUTPUT_FILE)
    return OUTPUT_FILE

def falar_resposta(texto):
    if not voz_ativa: return
    
    # Limpa o texto para não falar [STATUS] etc
    texto_limpo = re.sub(r'\[.*?\]', '', texto).replace('*', '').replace('VOCÊ DISSE:', '')
    
    if not texto_limpo.strip(): return

    try:
        # Cria um loop novo para rodar o async dentro do Streamlit
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        arquivo_audio = loop.run_until_complete(gerar_audio_neural(texto_limpo))
        
        # Toca o arquivo gerado
        st.audio(arquivo_audio, format='audio/mp3', start_time=0)
        
    except Exception as e:
        st.error(f"Erro no Módulo Neural: {e}")

def processar(texto_usuario=None, imagem_usuario=None, audio_usuario=None):
    lista_partes = []
    
    prompt_base = SYSTEM_INSTRUCTION
    if texto_usuario: prompt_base += f"\n\nUSUÁRIO (TEXTO): {texto_usuario}"
    lista_partes.append(Part(text=prompt_base))
    
    if imagem_usuario:
        img = Image.open(imagem_usuario)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        lista_partes.append(Part(inline_data={"mime_type": "image/jpeg", "data": buf.getvalue()}))
        
    if audio_usuario:
        lista_partes.append(Part(inline_data={"mime_type": "audio/wav", "data": audio_usuario.getvalue()}))

    if not texto_usuario and not imagem_usuario and not audio_usuario: return

    with st.spinner(">> PROCESSANDO DADOS NEURAIS..."):
        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=[Content(role="user", parts=lista_partes)]
            )
            
            resposta_full = response.text
            
            # Separação
            if "VOCÊ DISSE:" in resposta_full:
                partes = resposta_full.split("VOCÊ DISSE:")
                resto = partes[1].split("\n", 1)
                transcricao = resto[0].strip()
                resposta_helios = resto[1].strip() if len(resto) > 1 else ""
            else:
                transcricao = "Entrada Processada"
                resposta_helios = resposta_full

            # 1. Transcrição
            if transcricao:
                st.markdown(f"""<div class="user-box"><small style="color: #FFD700;">🎤 VOCÊ DISSE:</small><br><span style="color: #FFF;">"{transcricao}"</span></div>""", unsafe_allow_html=True)

            # 2. Resposta
            st.markdown(f"""<div class="helios-box"><strong style="color: #FFD700;">>> HELIOS RESPOSTA:</strong><br><br><span style="color: #FFF;">{resposta_helios}</span></div>""", unsafe_allow_html=True)
            
            # 3. Áudio Neural
            falar_resposta(resposta_helios)
                
        except Exception as e:
            st.error(f">> ERRO: {e}")

# --- INTERFACE ---
col_text, col_cam = st.columns(2)

with col_text:
    st.subheader(">> COMANDO DE VOZ / TEXTO")
    audio_rec = st.audio_input("GRAVAR")
    if audio_rec: processar(audio_usuario=audio_rec)
    
    st.markdown("--- OU ---")
    
    with st.form("form_txt"):
        txt = st.text_input("DIGITAR:")
        if st.form_submit_button("ENVIAR"): processar(texto_usuario=txt)

with col_cam:
    st.subheader(">> SENSOR VISUAL")
    cam = st.camera_input("ATIVAR")
    if cam and st.button("ANALISAR IMAGEM"):
        processar(imagem_usuario=cam, texto_usuario="Descreva esta imagem.")
