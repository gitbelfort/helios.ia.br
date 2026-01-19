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

# --- CONFIGURAÇÃO VISUAL TRON (CSS V2) ---
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    
    /* --- CSS DAS ABAS (CORREÇÃO DE CONTRASTE) --- */
    
    /* Container das abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        padding-bottom: 10px;
    }
    
    /* Aba INATIVA (Fundo Preto, Texto Amarelo) */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #000000;
        color: #FFD700;
        border: 1px solid #FFD700;
        border-radius: 0px;
        text-transform: uppercase;
        font-family: 'Share Tech Mono', monospace;
        font-size: 16px;
        font-weight: normal;
    }
    
    /* Aba ATIVA (Fundo Amarelo, Texto Preto) - Forçando com !important */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFD700 !important;
        color: #000000 !important;
        font-weight: 900 !important;
        border: 1px solid #FFD700;
    }
    
    /* Inputs, Botões e Caixas */
    .stTextInput > div > div > input { background-color: #111; color: #FFD700; border: 1px solid #FFD700; font-family: 'Share Tech Mono', monospace; }
    .stButton > button { background-color: #000000; color: #FFD700; border: 2px solid #FFD700; border-radius: 0px; transition: 0.3s; width: 100%; text-transform: uppercase; font-weight: bold;}
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 15px #FFD700; }
    
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    header {visibility: hidden;}
    
    .user-box { border: 1px dashed #FFD700; padding: 10px; margin-bottom: 10px; opacity: 0.8; font-size: 0.9em;}
    .helios-box { border: 1px solid #FFD700; padding: 20px; background-color: #050505; border-left: 5px solid #FFD700; margin-top: 10px; font-size: 1.1em;}
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE RESET (SESSION STATE) ---
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

def limpar_terminal():
    st.session_state.reset_counter += 1
    # st.rerun() não é necessário aqui pois o botão já recarrega, 
    # mas o contador muda as keys dos widgets, limpando-os.

# --- SIDEBAR ---
with st.sidebar:
    st.title("🟡 HELIOS v5.2")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    
    st.markdown("---")
    st.header(">> CONTROLE")
    voz_ativa = st.toggle("SINTETIZADOR DE VOZ", value=True)
    
    # Botão de Limpeza com Estilo de Perigo (Borda Vermelha simulada pelo Streamlit se possível, ou padrão)
    if st.button("♻️ LIMPAR TERMINAL"):
        limpar_terminal()
        
    st.markdown("---")
    st.info("DOMÍNIO: HELIOS.IA.BR")

if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

# --- LÓGICA DE VOZ ---
async def gerar_audio_neural(texto):
    OUTPUT_FILE = "helios_neural.mp3"
    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
    await communicate.save(OUTPUT_FILE)
    return OUTPUT_FILE

def falar(texto):
    if not voz_ativa: return
    clean_text = re.sub(r'\[.*?\]', '', texto).replace('*', '').replace('VOCÊ DISSE:', '').strip()
    if not clean_text: return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        arquivo = loop.run_until_complete(gerar_audio_neural(clean_text))
        with open(arquivo, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format='audio/mp3', start_time=0)
    except Exception as e:
        print(f"Erro Neural: {e} -> Fallback Web")
        try:
            texto_safe = urllib.parse.quote(clean_text[:200])
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={texto_safe}&tl=pt&client=tw-ob"
            st.audio(url, format='audio/mp3')
        except:
            pass

def processar_request(prompt_user, imagem=None, audio=None, modo_verbosidade="normal"):
    lista_partes = []
    
    # Prompt do Sistema
    base_prompt = "Você é o HELIOS. Responda em Português."
    if modo_verbosidade == "curto": base_prompt += " Seja breve. Uma frase."
    elif modo_verbosidade == "verboso": base_prompt += " Seja detalhista e completo."
    else: base_prompt += " Seja técnico e direto."
    
    if prompt_user: base_prompt += f"\n\nUSUÁRIO: {prompt_user}"
    lista_partes.append(Part(text=base_prompt))

    if imagem:
        img = Image.open(imagem)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        lista_partes.append(Part(inline_data={"mime_type": "image/jpeg", "data": buf.getvalue()}))
    
    if audio:
        lista_partes.append(Part(inline_data={"mime_type": "audio/wav", "data": audio.getvalue()}))

    with st.spinner(">> PROCESSANDO DADOS..."):
        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=[Content(role="user", parts=lista_partes)]
            )
            return response.text
        except Exception as e:
            st.error(f"Erro Cérebro: {e}")
            return None

# --- FRONTEND (ABAS) ---
# Usamos o reset_counter na KEY dos widgets. 
# Se o contador mudar, o Streamlit acha que são widgets novos e "reseta" eles.
id_sessao = st.session_state.reset_counter

tab1, tab2, tab3 = st.tabs(["MODO TEXTO", "MODO VOZ", "MODO VISAO"])

# === ABA 1: TEXTO ===
with tab1:
    st.subheader(">> TERMINAL DE TEXTO")
    with st.form(key=f"form_chat_{id_sessao}"):
        texto_input = st.text_input("COMANDO:", placeholder="Digite aqui...", key=f"txt_{id_sessao}")
        enviar = st.form_submit_button("ENVIAR")
    
    if enviar and texto_input:
        resp = processar_request(texto_input)
        if resp:
            st.markdown(f"""<div class="helios-box">{resp}</div>""", unsafe_allow_html=True)
            falar(resp)

# === ABA 2: VOZ ===
with tab2:
    st.subheader(">> INTERFACE DE VOZ")
    # O key dinâmico garante que o áudio suma quando limpar
    audio_rec = st.audio_input("GRAVAR ÁUDIO", key=f"audio_{id_sessao}")
    
    if audio_rec:
        resp = processar_request("Responda ao áudio.", audio=audio_rec)
        if resp:
            st.markdown(f"""<div class="helios-box">{resp}</div>""", unsafe_allow_html=True)
            falar(resp)

# === ABA 3: VISÃO ===
with tab3:
    st.subheader(">> ANÁLISE VISUAL")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.radio("VERBOSIDADE:", ["Curto", "Normal", "Verboso"], horizontal=True, key=f"radio_{id_sessao}")
    with col2:
        # Toggle para esconder a câmera se quiser
        preview = st.toggle("PREVIEW", value=True, key=f"toggle_{id_sessao}")
        
    st.markdown("---")
    
    img_file = st.camera_input("SENSOR", label_visibility="collapsed" if not preview else "visible", key=f"cam_{id_sessao}")
    
    if img_file:
        if st.button(">> ANALISAR CENA", key=f"btn_analisar_{id_sessao}", type="primary"):
            modo_map = {"Curto": "curto", "Normal": "normal", "Verboso": "verboso"}
            resp = processar_request("Descreva o que vê.", imagem=img_file, modo_verbosidade=modo_map[modo])
            
            if resp:
                st.markdown(f"""<div class="helios-box">[{modo.upper()}] >> {resp}</div>""", unsafe_allow_html=True)
                falar(resp)
