import streamlit as st
import os
import datetime
import time
import json
from google import genai
from google.genai import types
from PIL import Image
import io
import pypdf
import docx

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="HELIOS | SYSTEM", 
    page_icon="🟡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS GLOBAIS (TRON THEME TÁTICO E BLINDAGEM DE BOTÕES) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    [data-testid="stSidebar"] { display: none; }
    
    h1, h2, h3, p, label, span, div, li { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    /* Inputs e Dropdowns */
    .stTextInput, .stSelectbox, .stFileUploader, .stRadio, .stCheckbox, .stTextArea { color: #FFD700; }
    .stSelectbox > div > div, .stTextArea > div > textarea { background-color: #111; color: #FFD700; border: 1px solid #FFD700; font-size: 0.9rem;}
    
    .stTextInput > div > div > input { background-color: #111; color: #00FF00; border: 1px solid #00FF00; text-align: center; font-size: 1.2em; }

    /* BOTÕES TÁTICOS (REDUZIDOS E SEM ÍCONES) */
    button[kind="secondary"] { 
        background-color: transparent !important; border: 1px solid #FFD700 !important; border-radius: 0px; 
        transition: 0.2s; padding: 0.2rem 0.5rem !important; min-height: 35px !important;
    }
    button[kind="secondary"], button[kind="secondary"] * {
        color: #FFD700 !important; font-weight: normal; font-size: 0.85rem !important; text-transform: uppercase;
    }
    button[kind="secondary"]:hover, button[kind="secondary"]:focus, button[kind="secondary"]:active { 
        background-color: #FFD700 !important; box-shadow: 0 0 10px #FFD700 !important;
    }
    button[kind="secondary"]:hover *, button[kind="secondary"]:focus *, button[kind="secondary"]:active * {
        color: #000000 !important; 
    }

    button[kind="primary"] { 
        background-color: transparent !important; border: 1px solid #00FF00 !important; border-radius: 0px; 
        transition: 0.2s; padding: 0.2rem 0.5rem !important; min-height: 35px !important;
    }
    button[kind="primary"], button[kind="primary"] * {
        color: #00FF00 !important; font-weight: bold; font-size: 0.85rem !important; text-transform: uppercase;
    }
    button[kind="primary"]:hover, button[kind="primary"]:focus, button[kind="primary"]:active { 
        background-color: #00FF00 !important; box-shadow: 0 0 10px #00FF00 !important;
    }
    button[kind="primary"]:hover *, button[kind="primary"]:focus *, button[kind="primary"]:active * {
        color: #000000 !important; 
    }
    
    /* CORREÇÃO DO BOTÃO DE UPLOAD (BROWSE FILES) */
    [data-testid='stFileUploader'] { border: 1px dashed #FFD700; padding: 15px; background-color: #050505; }
    [data-testid='stFileUploader'] button {
        background-color: #111 !important; color: #FFD700 !important; border: 1px solid #FFD700 !important; transition: 0.2s;
    }
    [data-testid='stFileUploader'] button:hover, [data-testid='stFileUploader'] button:focus, [data-testid='stFileUploader'] button:active {
        background-color: #FFD700 !important;
    }
    [data-testid='stFileUploader'] button:hover *, [data-testid='stFileUploader'] button:focus *, [data-testid='stFileUploader'] button:active * {
        color: #000000 !important;
    }
    
    .analysis-box { border: 1px solid #333; background-color: #111; padding: 15px; margin-top: 10px; border-left: 3px solid #00FF00; font-size: 0.85rem; color: #EEE !important; }
    .instruction-box { border: 1px solid #FFD700; background-color: #0a0a0a; padding: 15px; margin-bottom: 25px; border-left: 5px solid #FFD700; font-size: 0.9rem;}
    .token-box { font-size: 0.75rem; color: #888 !important; margin-top: 10px; border-top: 1px solid #333; padding-top: 5px; }
    .privacy-text { text-align: center; color: #555 !important; font-size: 0.65rem; margin-top: 10px; border-top: 1px dashed #222; padding-top: 10px; line-height: 1.3; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #000000; color: #00FF00 !important; text-align: center; padding: 8px; font-size: 0.8rem; border-top: 1px solid #222; z-index: 999; font-family: 'Share Tech Mono', monospace; letter-spacing: 1px; }
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CAMADA DE SEGURANÇA (GATEKEEPER) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col_spacer1, col_login, col_spacer2 = st.columns([1, 2, 1])
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("🔒 ACESSO RESTRITO")
        senha_input = st.text_input("DIGITE A SENHA DE SEGURANÇA", type="password")
        if st.button("ENTRAR NO SISTEMA", type="primary", use_container_width=True):
            if "APP_PASSWORD" in st.secrets and senha_input == st.secrets["APP_PASSWORD"]:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("⛔ ACESSO NEGADO")
    st.stop()

# ==============================================================================
# HELIOS v9.3 CORE (VERTEX AI ENTERPRISE)
# ==============================================================================

# CONFIGURAÇÕES DA VERTEX AI (Puxando dos Secrets do Streamlit)
PROJECT_ID = st.secrets["GCP_PROJECT_ID"]
LOCATION = "us-central1" # Onde sua cota é de 1.500 RPM

# MODELOS (Nomes oficiais na Vertex AI)
MODELO_TEXTO_FIXO = "gemini-2.0-flash-001"
MODELO_IMAGEM_FIXO = "imagen-3.0-generate-001"

# CONFIGURAÇÃO DE CREDENCIAIS SEM ARQUIVO NO GIT
creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])

# Instanciando o Cliente Enterprise
client = genai.Client(
    vertexai=True, 
    project=PROJECT_ID, 
    location=LOCATION,
    credentials=creds_dict
)

KNOWLEDGE_BASE = """
    ACT AS THE WORLD'S ELITE PROMPT ENGINEER AND CINEMATOGRAPHER.
    Use terminology from photography and cinema: 30mm lens, f/1.4 aperture, bokeh, f/11 sharp landscapes.
    SHOTS: Aerial, Close-up, POV, Over-the-shoulder.
    LIGHTING: Backlight, Key light, Practical light, Diegetic lighting, Tungsten (3200K).
    CAMERA MOVEMENTS: Pan, Tilt, Zoom, Steadicam.
    RENDER: 8k resolution, photorealistic, ProRes quality.
"""

ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic. Intense action frames, dramatic energy effects.",
    "3D NEUMORPHISM AESTHETIC": "Tactile 3D Neumorphism. Ultra-soft UI elements, soft shadows.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography. Studio lighting, sharp textures.",
    "RETRO-FUTURISM": "Nostalgic Sci-Fi. Neon lighting (teals/purples), film grain.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast. Massive heavy typography, brutalist shapes."
}

keys_to_init = [
    'last_image_bytes', 'last_token_usage', 'reset_trigger', 
    'analyzed_content', 'file_type_detected', 'last_uploaded_file_id',
    'security_check_passed', 'clean_prompt_content', 'original_image_part',
    'generated_prompt_img', 'generated_prompt_vid', 'generated_script'
]
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'reset_trigger' else 0

def reset_all():
    for key in keys_to_init:
        if key != 'reset_trigger': st.session_state[key] = None
    st.session_state.reset_trigger += 1

# --- 🛡️ ESCUDO ANTI-429 (EXPONENTIAL BACKOFF) ---
def generate_content_with_retry(model_name, contents, config=None, max_retries=4):
    delay = 2
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model=model_name, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e).lower() or "quota" in str(e).lower():
                if attempt == max_retries - 1: raise e
                time.sleep(delay)
                delay *= 2
            else: raise e

# --- FUNÇÕES NÚCLEO ---
def process_uploaded_file(uploaded_file):
    try:
        if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            return types.Part(inline_data=types.Blob(mime_type=uploaded_file.type, data=uploaded_file.getvalue())), "IMAGE"
        text_content = ""
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages: text_content += page.extract_text() + "\n"
        elif "wordprocessingml" in uploaded_file.type:
            doc = docx.Document(uploaded_file)
            text_content = "\n".join([p.text for p in doc.paragraphs])
        else: text_content = uploaded_file.read().decode("utf-8")
        return text_content, "TEXT"
    except Exception: return None, None

def initial_analysis(content_data, file_type):
    try:
        c_part = types.Part.from_text(text=content_data) if file_type == "TEXT" else content_data
        response = generate_content_with_retry(model_name=MODELO_TEXTO_FIXO, contents=[types.Part.from_text(text="Identifique o conteúdo em Português."), c_part])
        return response.text
    except Exception: return "Conteúdo carregado."

def generate_image_pixels(prompt_text, aspect_ratio, reference_image=None):
    ar = "1:1"
    if "16:9" in aspect_ratio: ar = "16:9"
    elif "9:16" in aspect_ratio: ar = "9:16"
    
    generation_contents = [types.Part.from_text(text=prompt_text)]
    if reference_image: generation_contents.append(reference_image)
    config_img = types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio=ar))

    try:
        response = generate_content_with_retry(model_name=MODELO_IMAGEM_FIXO, contents=generation_contents, config=config_img)
        for part in response.parts:
            if part.inline_data: return part.inline_data.data
        return None
    except Exception as e:
        st.error(f"Erro no Motor Visual Enterprise: {e}")
        return None

# ==============================================================================
# UI PRINCIPAL
# ==============================================================================
st.title("🟡 HELIOS // ENTERPRISE v9.3")

st.markdown("""<div class="instruction-box"><strong>MANUAL v9.3:</strong> Sistema conectado à Vertex AI (us-central1). Alta cota de processamento ativa.</div>""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. INPUT UNIVERSAL")
    uploaded_file = st.file_uploader("ARQUIVO BASE", type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"], key=f"up_{reset_k}")

    if uploaded_file:
        current_id = uploaded_file.file_id if hasattr(uploaded_file, 'file_id') else uploaded_file.name
        if current_id != st.session_state.last_uploaded_file_id:
            with st.spinner("CONECTANDO À VERTEX AI..."):
                content_raw, ftype = process_uploaded_file(uploaded_file)
                if content_raw:
                    st.session_state.security_check_passed = True
                    st.session_state.clean_prompt_content = content_raw
                    st.session_state.file_type_detected = ftype
                    st.session_state.analyzed_content = initial_analysis(content_raw, ftype)
                    st.session_state.last_uploaded_file_id = current_id

        if st.session_state.analyzed_content:
            st.markdown(f"""<div class="analysis-box">✅ {st.session_state.analyzed_content}</div>""", unsafe_allow_html=True)

    st.subheader(">> 2. CONFIGURAÇÃO")
    modo_imagem = st.selectbox("MODO", ["APLICAR ESTILO VISUAL", "CRIAR INFOGRÁFICO", "RESTAURAR FOTO"], key=f"mode_{reset_k}")
    fmt = st.selectbox("FORMATO", ["16:9", "9:16", "1:1", "4:3"], key=f"fmt_{reset_k}")
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        if st.button("GERAR IMAGEM", type="primary", use_container_width=True, key=f"gen_{reset_k}"):
            with st.spinner("RENDERIZANDO VIA VERTEX AI..."):
                img_bytes = generate_image_pixels("Cinematic high quality image based on input.", fmt)
                if img_bytes:
                    st.session_state.last_image_bytes = img_bytes
                    st.rerun()
    with b_col2:
        if st.button("LIMPAR", type="secondary", use_container_width=True, key=f"clr_{reset_k}"):
            reset_all(); st.rerun()

with col2:
    st.subheader(">> 3. RESULTADO")
    if st.session_state.last_image_bytes:
        st.image(Image.open(io.BytesIO(st.session_state.last_image_bytes)), use_container_width=True)
        st.download_button("BAIXAR PNG", data=st.session_state.last_image_bytes, file_name="helios.png", type="secondary")
    else: st.info("Aguardando comando...")

st.markdown("""<div class="footer">CONEXÃO ESTABELECIDA: VERTEX-AI-US-CENTRAL1 | HELIOS.IA.BR</div>""", unsafe_allow_html=True)
