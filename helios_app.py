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

# --- CONFIGURAÇÃO VISUAL TRON (CSS V4 - CLEAN) ---
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    
    /* --- REMOVENDO O CABEÇALHO PADRÃO (Tira o keyboard_double_arrow...) --- */
    header[data-testid="stHeader"] {
        display: none;
    }
    .stDeployButton {
        display: none;
    }
    
    /* --- CSS DAS ABAS --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        padding-bottom: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #050505;
        color: #666;
        border: 1px solid #333;
        border-radius: 4px;
        text-transform: uppercase;
        font-family: 'Share Tech Mono', monospace;
        font-size: 16px;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #000000 !important;
        color: #FFD700 !important;
        border: 2px solid #FFD700 !important;
        border-radius: 4px;
        font-weight: bold;
        box-shadow: 0 0 8px rgba(255, 215, 0, 0.4);
    }
    
    /* Inputs, Botões e Caixas */
    .stTextInput > div > div > input { background-color: #111; color: #FFD700; border: 1px solid #FFD700; font-family: 'Share Tech Mono', monospace; }
    .stButton > button { background-color: #000000; color: #FFD700; border: 2px solid #FFD700; border-radius: 0px; transition: 0.3s; width: 100%; text-transform: uppercase; font-weight: bold;}
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 15px #FFD700; }
    
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    .user-box { border: 1px dashed #FFD700; padding: 10px; margin-bottom: 10px; opacity: 0.8; font-size: 0.9em;}
    .helios-box { border: 1px solid #FFD700; padding: 20px; background-color: #050505; border-left: 5px solid #FFD700; margin-top: 10px; font-size: 1.1em;}
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE RESET ---
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

def limpar_terminal():
    st.session_state.reset_counter += 1

# --- SIDEBAR ---
with st.sidebar:
    st.title("🟡 HELIOS v5.4")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    
    st.markdown("---")
    st.header(">> ÁUDIO")
    # Explicação: Este botão liga/desliga o som geral
    voz_ativa = st.toggle("ATIVAR FALAS (VOZ)", value=True)
    
    # Seletor de Voz para testar qual soa menos robótica
    tipo_voz = st.radio("MODELO DE VOZ:", ["Masculina (Antonio)", "Feminina (Francisca)"])
    
    # Mapeamento para o código da Microsoft
    voz_code = "pt-BR-AntonioNeural" if "Masculina" in tipo_voz else "pt-BR-FranciscaNeural"
    
    st.markdown("---")
    if st.button("♻️ LIMPAR TERMINAL"):
        limpar_terminal()
        
    st.info("DOMÍNIO: HELIOS.IA.BR")

if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

# --- LÓGICA DE VOZ ---
async def gerar_audio_neural(texto, voz_selecionada):
    OUTPUT_FILE = "helios_neural.mp3"
    communicate = edge_tts.Communicate(texto, voz_selecionada)
    await communicate.save(OUTPUT_FILE)
    return OUTPUT_FILE

def falar(texto):
    if not voz_ativa: return
    clean_text = re.sub(r'\[.*?\]', '', texto).replace('*', '').replace('VOCÊ DISSE:', '').strip()
    if not clean_text: return

    try:
        # Tenta a voz Neural (Boa qualidade)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        arquivo = loop.run_until_complete(gerar_audio_neural(clean_text, voz_code))
        with open(arquivo, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format='audio/mp3', start_time=0)
    except Exception as e:
        # Fallback Web (Voz Robótica de Segurança)
        # Se cair aqui, avisa o usuário
        print(f"Erro Neural: {e}")
        st.toast("⚠️ Falha na Neural. Usando voz de backup.", icon="⚠️")
        try:
            texto_safe = urllib.parse.quote(clean_text[:200])
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={texto_safe}&tl=pt&client=tw-ob"
            st.audio(url, format='audio/mp3')
        except:
            pass

def processar_request(prompt_user, imagem=None, audio=None, modo_verbosidade="normal"):
    lista_partes = []
    
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

# --- FRONTEND ---
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
        preview = st.toggle("ATIVAR SENSOR VISUAL", value=True, key=f"toggle_{id_sessao}")
        
    st.markdown("---")
    
    if preview:
        img_file = st.camera_input("SENSOR", label_visibility="collapsed", key=f"cam_{id_sessao}")
        if img_file:
            if st.button(">> ANALISAR CENA", key=f"btn_analisar_{id_sessao}", type="primary"):
                modo_map = {"Curto": "curto", "Normal": "normal", "Verboso": "verboso"}
                resp = processar_request("Descreva o que vê.", imagem=img_file, modo_verbosidade=modo_map[modo])
                if resp:
                    st.markdown(f"""<div class="helios-box">[{modo.upper()}] >> {resp}</div>""", unsafe_allow_html=True)
                    falar(resp)
    else:
        st.info(">> SENSOR VISUAL EM STANDBY (OFFLINE)")
