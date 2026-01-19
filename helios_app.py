import streamlit as st
import os
from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io
import urllib.parse
import re # Biblioteca para limpar o texto (Regex)

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
with col2: st.title("HELIOS // SYSTEM v3.3")

st.markdown("`[STATUS: MÓDULO DE TRANSCRIÇÃO ATIVO]`")
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

# Prompt Ajustado para Transcrição
SYSTEM_INSTRUCTION = """
INSTRUÇÃO DE SISTEMA: Você é o HELIOS.
IMPORTANTE: Sua resposta deve ter DUAS partes separadas.
1. Primeiro, escreva exatamente o que você ouviu ou entendeu do usuário, começando com "VOCÊ DISSE:".
2. Pule uma linha e dê sua resposta técnica como HELIOS (Use [STATUS], >>).
Exemplo:
VOCÊ DISSE: Qual a temperatura?
[STATUS: OK] >> A temperatura atual é...
"""

def limpar_texto_para_audio(texto_bruto):
    """Remove caracteres especiais que travam o Google TTS"""
    # Remove tudo entre colchetes [STATUS]
    limpo = re.sub(r'\[.*?\]', '', texto_bruto)
    # Remove símbolos >>, *, #
    limpo = limpo.replace('>>', '').replace('*', '').replace('#', '').replace('VOCÊ DISSE:', '')
    return limpo.strip()

def falar_resposta(texto):
    """Gera áudio usando API Web com texto limpo"""
    if voz_ativa:
        try:
            # Limpa o texto antes de enviar para o áudio
            texto_fala = limpar_texto_para_audio(texto)
            
            # Se ficou vazio (só tinha símbolos), não fala nada
            if len(texto_fala) < 2: return

            texto_safe = urllib.parse.quote(texto_fala)
            url_audio = f"https://translate.google.com/translate_tts?ie=UTF-8&q={texto_safe}&tl=pt&client=tw-ob"
            
            st.markdown(f"""
                <audio autoplay="true" style="display:none;">
                <source src="{url_audio}" type="audio/mp3">
                </audio>
            """, unsafe_allow_html=True)
            
            # Player visível para replay
            st.audio(url_audio, format='audio/mp3')
            
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
            
            resposta_completa = response.text
            
            # Tenta separar o que é transcrição do que é resposta do Helios
            partes = resposta_completa.split("VOCÊ DISSE:")
            
            if len(partes) > 1:
                # Se o modelo obedeceu, separamos visualmente
                resto = partes[1].split("\n", 1) # Pega a primeira linha como transcrição
                transcricao_usuario = resto[0].strip()
                resposta_helios = resto[1].strip() if len(resto) > 1 else ""
            else:
                # Fallback se ele não separar
                transcricao_usuario = "Entrada de Áudio/Imagem Processada"
                resposta_helios = resposta_completa

            # 1. Exibe a Transcrição do Usuário
            if transcricao_usuario:
                st.markdown(f"""
                <div class="user-box">
                <small style="color: #FFD700;">🎤 TRANSCRIÇÃO (VOCÊ):</small><br>
                <span style="color: #FFF;">"{transcricao_usuario}"</span>
                </div>
                """, unsafe_allow_html=True)

            # 2. Exibe a Resposta do Helios
            st.markdown(f"""
            <div class="helios-box">
            <strong style="color: #FFD700;">>> HELIOS RESPOSTA:</strong><br><br>
            <span style="color: #FFF;">{resposta_helios}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. Gera o Áudio (apenas da resposta do Helios, limpa)
            falar_resposta(resposta_helios)
                
        except Exception as e:
            st.error(f">> ERRO DE COMUNICAÇÃO: {e}")

# --- INTERFACE PRINCIPAL ---

col_text, col_cam = st.columns(2)

with col_text:
    st.subheader(">> COMANDO DE VOZ / TEXTO")
    
    audio_rec = st.audio_input("GRAVAR COMANDO DE VOZ")
    if audio_rec:
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
