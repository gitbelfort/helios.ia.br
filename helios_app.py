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
    
    /* Tabs (Abas) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #0a0a0a; border: 1px solid #FFD700; color: #FFD700;
        border-radius: 0px; text-transform: uppercase;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFD700; color: #000000; font-weight: bold;
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

# --- SIDEBAR (CONFIGURAÇÕES GERAIS) ---
with st.sidebar:
    st.title("🟡 HELIOS v5.0")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    
    st.markdown("---")
    st.header(">> SISTEMA")
    voz_ativa = st.toggle("SINTETIZADOR DE VOZ", value=True)
    # Nova voz: Donato (Mais natural que Antonio)
    VOZ_MODELO = "pt-BR-DonatoNeural" 
    
    st.info("DOMÍNIO: HELIOS.IA.BR")

# --- LÓGICA DO CÉREBRO ---
if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODELO = "gemini-2.0-flash-exp"

# --- FUNÇÕES ---

async def gerar_audio_neural(texto):
    """Gera áudio com a voz Donato Neural"""
    OUTPUT_FILE = "helios_response.mp3"
    communicate = edge_tts.Communicate(texto, VOZ_MODELO)
    await communicate.save(OUTPUT_FILE)
    return OUTPUT_FILE

def falar(texto):
    if not voz_ativa: return
    # Limpeza para não falar besteira
    clean_text = re.sub(r'\[.*?\]', '', texto).replace('*', '').replace('VOCÊ DISSE:', '')
    if not clean_text.strip(): return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        arquivo = loop.run_until_complete(gerar_audio_neural(clean_text))
        st.audio(arquivo, format='audio/mp3', start_time=0)
    except Exception as e:
        st.error(f"Erro Voz: {e}")

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
    
    # Adiciona instrução do sistema
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
            st.error(f"Erro: {e}")
            return None

# --- INTERFACE DE ABAS (O FRONTEND) ---

# Criação das 3 Abas
tab_texto, tab_voz, tab_visao = st.tabs(["📝 MODO TEXTO", "🎙️ MODO VOZ", "👁️ MODO VISÃO"])

# === ABA 1: TEXTO ===
with tab_texto:
    st.subheader(">> TERMINAL DE TEXTO")
    
    # Histórico de Chat Simulado (Só mostra a última interação por enquanto para ser rápido)
    with st.form("chat_form"):
        texto_input = st.text_input("DIGITE SEU COMANDO:", placeholder="Ex: Crie um código python...")
        enviar_texto = st.form_submit_button("ENVIAR MENSAGEM")
    
    if enviar_texto and texto_input:
        resp = processar_request(texto_input)
        if resp:
            st.markdown(f"""<div class="helios-box">{resp}</div>""", unsafe_allow_html=True)
            falar(resp)

# === ABA 2: VOZ ===
with tab_voz:
    st.subheader(">> INTERFACE DE VOZ")
    st.markdown("`[STATUS: AGUARDANDO COMANDO SONORO]`")
    
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        st.markdown("### 🎙️")
    with col_v2:
        audio_rec = st.audio_input("TOQUE PARA FALAR")
    
    if audio_rec:
        # No modo voz, assumimos que você quer uma resposta falada
        resp = processar_request("Responda ao áudio.", audio=audio_rec)
        if resp:
            st.markdown(f"""<div class="user-box">ÁUDIO PROCESSADO</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="helios-box">{resp}</div>""", unsafe_allow_html=True)
            falar(resp)

# === ABA 3: VISÃO ===
with tab_visao:
    st.subheader(">> ANÁLISE VISUAL EM TEMPO REAL")
    
    # Controles da Visão
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        modo_visao = st.radio("VERBOSIDADE:", ["Curto", "Normal", "Verboso"], horizontal=True)
    with col_conf2:
        mostrar_preview = st.toggle("MOSTRAR PREVIEW DA CÂMERA", value=True)
    
    st.markdown("---")
    
    # Câmera
    img_file = st.camera_input("SENSOR ÓPTICO", label_visibility="collapsed" if not mostrar_preview else "visible")
    
    # Botão de Transmissão (Simulado)
    # Nota: Streamlit não deixa fazer loop infinito com camera_input sem travar.
    # O usuário precisa clicar para 'atualizar' a visão por enquanto.
    if img_file:
        botao_analisar = st.button(">> ANALISAR CENA ATUAL", type="primary")
        
        if botao_analisar:
            # Converte modo para chave interna
            modo_map = {"Curto": "curto", "Normal": "normal", "Verboso": "verboso"}
            
            prompt_visao = "Descreva o que você vê conforme o nível de detalhe solicitado."
            resp = processar_request(prompt_visao, imagem=img_file, modo_verbosidade=modo_map[modo_visao])
            
            if resp:
                st.markdown(f"""<div class="helios-box">[{modo_visao.upper()}] >> {resp}</div>""", unsafe_allow_html=True)
                falar(resp)
