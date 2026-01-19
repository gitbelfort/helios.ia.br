import streamlit as st
import os
from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io
import urllib.parse
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
    
    /* Texto */
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    header {visibility: hidden;}
    
    /* Caixas de Texto */
    .user-box {
        border: 1px dashed #FFD700; padding: 10px; margin-bottom: 10px; opacity: 0.8;
    }
    .helios-box {
        border: 1px solid #FFD700; padding: 20px; background-color: #050505; 
        border-left: 5px solid #FFD700; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 10])
with col1: st.title("🟡")
with col2: st.title("HELIOS // SYSTEM v3.4")

st.markdown("`[STATUS: AUDIO LONG-RANGE ATIVO]`")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header(">> CONFIGURAÇÃO")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    voz_ativa = st.toggle("RESPOSTA DE VOZ", value=True)
    st.info("DOMÍNIO: HELIOS.IA.BR")

# --- LÓGICA ---
if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

# Prompt Ajustado
SYSTEM_INSTRUCTION = """
INSTRUÇÃO DE SISTEMA: Você é o HELIOS.
IMPORTANTE: Sua resposta deve ter DUAS partes.
1. Comece com "VOCÊ DISSE: [O que você entendeu]".
2. Pule uma linha e dê sua resposta técnica (Use [STATUS], >>).
"""

def limpar_texto(texto):
    """Remove formatação para leitura de voz"""
    texto = re.sub(r'\[.*?\]', '', texto) # Remove [STATUS]
    texto = texto.replace('*', '').replace('#', '').replace('VOCÊ DISSE:', '')
    return texto.strip()

def falar_resposta(texto):
    """Sistema Híbrido de Voz: gTTS (Principal) -> Web (Fallback)"""
    if not voz_ativa: return
    
    texto_limpo = limpar_texto(texto)
    if not texto_limpo: return

    # TENTATIVA 1: gTTS (Melhor qualidade, sem limite de tamanho)
    try:
        from gTTS import gTTS
        tts = gTTS(text=texto_limpo, lang='pt', slow=False)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        st.audio(audio_bytes, format='audio/mp3', start_time=0)
        return # Se deu certo, para aqui.
        
    except Exception as e:
        print(f"Erro gTTS: {e}")
        # Se falhar, vai para a Tentativa 2
        pass

    # TENTATIVA 2: Web Hack (Fallback para não ficar mudo)
    try:
        # Corta em 200 caracteres para não travar o link do Google
        resumo = texto_limpo[:200] + "..."
        texto_safe = urllib.parse.quote(resumo)
        url_audio = f"https://translate.google.com/translate_tts?ie=UTF-8&q={texto_safe}&tl=pt&client=tw-ob"
        
        st.warning("⚠️ [MODO DE VOZ WEB: LEITURA RESUMIDA]")
        st.audio(url_audio, format='audio/mp3')
    except:
        st.error(">> FALHA TOTAL NO SISTEMA DE ÁUDIO")

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
            
            # Separa Transcrição da Resposta
            if "VOCÊ DISSE:" in resposta_full:
                partes = resposta_full.split("VOCÊ DISSE:")
                resto = partes[1].split("\n", 1)
                transcricao = resto[0].strip()
                resposta_helios = resto[1].strip() if len(resto) > 1 else ""
            else:
                transcricao = "Entrada Processada"
                resposta_helios = resposta_full

            # 1. Mostra Transcrição
            if transcricao:
                st.markdown(f"""
                <div class="user-box">
                <small style="color: #FFD700;">🎤 VOCÊ DISSE:</small><br>
                <span style="color: #FFF;">"{transcricao}"</span>
                </div>
                """, unsafe_allow_html=True)

            # 2. Mostra Resposta
            st.markdown(f"""
            <div class="helios-box">
            <strong style="color: #FFD700;">>> HELIOS RESPOSTA:</strong><br><br>
            <span style="color: #FFF;">{resposta_helios}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. Fala
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
