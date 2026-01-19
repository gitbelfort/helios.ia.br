import streamlit as st
import os
import asyncio
import edge_tts
from google import genai
from google.genai.types import Content, Part
from PIL import Image
import io
import re
import urllib.parse

# --- CONFIGURAÇÃO VISUAL TRON ---
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    
    /* --- ESTILO DAS ABAS (CORRIGIDO) --- */
    /* Remove a barra superior padrão das abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    /* Aba Não Selecionada */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #111111;
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 0px;
        text-transform: uppercase;
        font-family: 'Share Tech Mono', monospace;
        font-size: 18px;
    }
    
    /* Aba Selecionada (Onde estava invisível) */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFD700 !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #FFD700;
    }
    
    /* Inputs e Botões */
    .stTextInput > div > div > input { background-color: #111; color: #FFD700; border: 1px solid #FFD700; }
    .stButton > button { background-color: #000000; color: #FFD700; border: 2px solid #FFD700; border-radius: 0px; transition: 0.3s; width: 100%; text-transform: uppercase;}
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 15px #FFD700; }
    
    /* Elementos de Texto */
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    header {visibility: hidden;}
    
    /* Caixas de Diálogo */
    .user-box { border: 1px dashed #FFD700; padding: 10px; margin-bottom: 10px; opacity: 0.8; font-size: 0.9em;}
    .helios-box { border: 1px solid #FFD700; padding: 20px; background-color: #050505; border-left: 5px solid #FFD700; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🟡 HELIOS v5.1")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    st.markdown("---")
    st.header(">> SISTEMA")
    voz_ativa = st.toggle("SINTETIZADOR DE VOZ", value=True)
    st.info("DOMÍNIO: HELIOS.IA.BR")

if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

# --- SISTEMA DE VOZ HÍBRIDO (NEURAL + WEB) ---

async def gerar_audio_neural(texto):
    """Tenta gerar áudio Neural (Microsoft)"""
    OUTPUT_FILE = "helios_neural.mp3"
    # Trocando para Antonio (mais estável que Donato)
    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
    await communicate.save(OUTPUT_FILE)
    return OUTPUT_FILE

def falar(texto):
    if not voz_ativa: return
    
    # Limpeza básica
    clean_text = re.sub(r'\[.*?\]', '', texto).replace('*', '').replace('VOCÊ DISSE:', '')
    clean_text = clean_text.strip()
    
    if not clean_text: return

    # TENTATIVA 1: MODO NEURAL (Alta Qualidade)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        arquivo = loop.run_until_complete(gerar_audio_neural(clean_text))
        
        # Lê o arquivo para memória para evitar travamento de arquivo aberto
        with open(arquivo, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format='audio/mp3', start_time=0)
        
    except Exception as e:
        # TENTATIVA 2: MODO WEB (Fallback se o Neural falhar)
        # Isso resolve o erro "No audio was received" - ele cai pra cá
        print(f"Erro Neural: {e} -> Usando Fallback Web")
        try:
            texto_safe = urllib.parse.quote(clean_text[:200]) # Limite seguro para web
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={texto_safe}&tl=pt&client=tw-ob"
            st.audio(url, format='audio/mp3')
        except:
            st.error("ERRO CRÍTICO NOS DOIS SISTEMAS DE VOZ.")

def get_system_prompt(modo="normal"):
    base = "Você é o HELIOS. Fale Português."
    if modo == "curto":
        return base + " Seja extremamente breve. Respostas de uma frase."
    elif modo == "verboso":
        return base + " Seja detalhista, analítico e profundo."
    else:
        return base + " Seja técnico, conciso e direto."

def processar_request(prompt_user, imagem=None, audio=None, modo_verbosidade="normal"):
    lista_partes = []
    
    sys_instruction = get_system_prompt(modo_verbosidade)
    if prompt_user: sys_instruction += f"\n\nUSUÁRIO: {prompt_user}"
    
    lista_partes.append(Part(text=sys_instruction))

    if imagem:
        img = Image.open(imagem)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        lista_partes.append(Part(inline_data={"mime_type": "image/jpeg", "data": buf.getvalue()}))
    
    if audio:
        lista_partes.append(Part(inline_data={"mime_type": "audio/wav", "data": audio.getvalue()}))

    with st.spinner(">> PROCESSANDO..."):
        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=[Content(role="user", parts=lista_partes)]
            )
            return response.text
        except Exception as e:
            st.error(f"Erro Cérebro: {e}")
            return None

# --- FRONTEND (ABAS CORRIGIDAS) ---

# Definição das Abas sem Ícones
tab1, tab2, tab3 = st.tabs(["MODO TEXTO", "MODO VOZ", "MODO VISAO"])

# === ABA 1: TEXTO ===
with tab1:
    st.subheader(">> TERMINAL DE TEXTO")
    with st.form("chat_form"):
        texto_input = st.text_input("DIGITE SEU COMANDO:", placeholder="aguardando entrada...")
        enviar_texto = st.form_submit_button("ENVIAR MENSAGEM")
    
    if enviar_texto and texto_input:
        resp = processar_request(texto_input)
        if resp:
            st.markdown(f"""<div class="helios-box">{resp}</div>""", unsafe_allow_html=True)
            falar(resp)

# === ABA 2: VOZ ===
with tab2:
    st.subheader(">> INTERFACE DE VOZ")
    
    audio_rec = st.audio_input("GRAVAR ÁUDIO")
    
    if audio_rec:
        resp = processar_request("Responda ao áudio.", audio=audio_rec)
        if resp:
            st.markdown(f"""<div class="helios-box">{resp}</div>""", unsafe_allow_html=True)
            falar(resp)

# === ABA 3: VISÃO ===
with tab3:
    st.subheader(">> ANÁLISE VISUAL")
    
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        modo_visao = st.radio("VERBOSIDADE:", ["Curto", "Normal", "Verboso"], horizontal=True)
    with col_conf2:
        mostrar_preview = st.toggle("MOSTRAR CÂMERA", value=True)
    
    st.markdown("---")
    
    # Label visibility collapsed remove o texto "Label" chato
    img_file = st.camera_input("SENSOR", label_visibility="collapsed" if not mostrar_preview else "visible")
    
    if img_file:
        botao_analisar = st.button(">> ANALISAR CENA ATUAL", type="primary")
        
        if botao_analisar:
            modo_map = {"Curto": "curto", "Normal": "normal", "Verboso": "verboso"}
            prompt_visao = "Descreva o que você vê."
            
            resp = processar_request(prompt_visao, imagem=img_file, modo_verbosidade=modo_map[modo_visao])
            
            if resp:
                st.markdown(f"""<div class="helios-box">[{modo_visao.upper()}] >> {resp}</div>""", unsafe_allow_html=True)
                falar(resp)
