import streamlit as st
import os
import datetime
from google import genai
from google.genai import types
from PIL import Image
import io
import pypdf
import docx

# --- CONFIGURAÇÃO VISUAL TRON ---
st.set_page_config(page_title="HELIOS | UNIVERSAL GEN", page_icon="🟡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    
    h1, h2, h3, p, label, span, div, li { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    .stTextInput, .stSelectbox, .stFileUploader { color: #FFD700; }
    .stSelectbox > div > div { background-color: #111; color: #FFD700; border: 1px solid #FFD700; }
    
    .stButton > button { 
        background-color: #000000; color: #FFD700; border: 2px solid #FFD700; 
        border-radius: 0px; text-transform: uppercase; transition: 0.3s; width: 100%; font-weight: bold; font-size: 1.1em;
    }
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 20px #FFD700; }
    
    [data-testid='stFileUploader'] { border: 1px dashed #FFD700; padding: 20px; background-color: #050505; }
    
    .token-box {
        font-size: 0.8em;
        color: #888 !important;
        margin-top: 10px;
        border-top: 1px solid #333;
        padding-top: 5px;
    }
    
    div[data-testid="stDialog"] {
        background-color: #000000;
        border: 2px solid #FFD700;
    }

    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- MODELO ---
MODELO_IMAGEM_FIXO = "gemini-3-pro-image-preview"

# --- ESTADO ---
if 'last_image_bytes' not in st.session_state:
    st.session_state.last_image_bytes = None
if 'last_token_usage' not in st.session_state:
    st.session_state.last_token_usage = None
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

def reset_all():
    st.session_state.last_image_bytes = None
    st.session_state.last_token_usage = None
    st.session_state.reset_trigger += 1

# --- ESTILOS ---
ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic illustration. A blend of intense action manga frames and vibrant, modern anime coloring. Dramatic energy effects, sharp angles. Colors are intense and saturated.",
    "3D NEUMORPHISM AESTHETIC": "Tactile 3D Neumorphism aesthetic illustration. Modern UI design, satisfying digital objects. Ultra-soft UI elements, extruded shapes, realistic soft shadows. Clean, minimalist palette.",
    "90s/Y2K PIXEL AESTHETIC": "90s/Y2K Retro Video Game aesthetic illustration. 16-bit pixel art, early internet culture. Bright neon colors, chunky rounded typography, pixelated icons. CRT monitor scanline effect.",
    "WHITEBOARD ANIMATION": "Classic Whiteboard Animation aesthetic illustration. Hand-drawn dry-erase marker sketches. Clean bright white background with subtle marker residue. Educational tone.",
    "MINI WORLD (DIORAMA)": "Isometric Miniature Diorama Aesthetic. Playful voxel art and macro photography. Tiny, living model kit. Vibrant colors, soft 'toy-like' textures. Tilt-shift effect.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography. Modern lifestyle aesthetic. Sophisticated interior design, minimalist decor. Soft natural lighting. Sharp details, realistic textures.",
    "RETRO-FUTURISM": "Nostalgic Retro Futurism Aesthetic. 90s sci-fi warmth, modern digital sharpness. Neon lighting, chrome surfaces, technological overlays. Cinematic film grain.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast Aesthetic. Massive, heavy typography and brutalist geometric shapes. Strict Black & White palette with one neon accent. Urgent, impactful."
}

# --- AUTH ---
with st.sidebar:
    st.title("🟡 HELIOS")
    st.markdown("**UNIVERSAL INFOGRAPHIC GEN**")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    st.markdown("---")
    if st.button("♻️ LIMPAR / NOVA GERAÇÃO"):
        reset_all()
        st.rerun()
    st.info("SISTEMA ONLINE\nDOMÍNIO: HELIOS.IA.BR")

if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

# --- FUNÇÕES ---

def process_uploaded_file(uploaded_file):
    try:
        # IMAGEM
        if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            return types.Part.from_bytes(uploaded_file.getvalue(), mime_type=uploaded_file.type)
        
        # TEXTO
        text_content = ""
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
        elif "wordprocessingml" in uploaded_file.type:
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        else: # txt
            text_content = uploaded_file.read().decode("utf-8")
            
        return types.Part.from_text(text=text_content[:20000]) 

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return None

def create_super_prompt(content_part, style_name, idioma, densidade):
    # Lógica de Inteligência EXPANDIDA para qualquer objeto
    prompt_text = f"""
    ROLE: You are an Elite Content Analyst and Art Director using Gemini Image Generation.
    TASK: Analyze the provided Input (Text or Image) and generate a detailed IMAGE PROMPT for an infographic.

    INPUT ANALYSIS & CLASSIFICATION LOGIC:
    1.  **IF TEXT/RESUME:** Create a "Career Timeline" infographic. Extract roles, skills, dates.
    2.  **IF IMAGE IS A DISH/FOOD:** Identify it. Create a "Recipe & Variations" infographic.
    3.  **IF IMAGE IS A PLACE/MONUMENT:** Identify it. Create a "Travel Guide & History" infographic.
    4.  **IF IMAGE IS A LIVING BEING (Animal/Plant/Pet):** Identify the species/breed. Create a "Biology, Care & Fun Facts" infographic.
    5.  **IF IMAGE IS A PHYSICAL OBJECT (Gadget/Tool/Toy/Furniture/Car):** Identify the item. Create a "Technical Specs, History & Utility" infographic. Break down its parts or explain how it works.
    6.  **IF IMAGE IS A CHARACTER/ART:** Analyze the design. Create a "Character Lore & Stats" infographic.
    7.  **IF IMAGE IS UNCLEAR:** OUTPUT EXACTLY: "INVALID_CONTENT".

    OUTPUT CONFIGURATION:
    -   Target Style: {style_name}
    -   Target Language (FOR THE TEXT INSIDE IMAGE): {idioma}
    -   Density: {densidade}

    INSTRUCTIONS FOR THE FINAL PROMPT:
    -   Write a single, descriptive prompt for an image generator (Nano Banana).
    -   Explicitly command: "Render all visible text in {idioma}".
    -   Describe the layout, the central subject, and the surrounding data blocks (text/charts).
    
    START OUTPUT WITH: "A high-resolution, text-rich infographic in {style_name} style..."
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Part.from_text(text=prompt_text),
                content_part
            ]
        )
        
        result_text = response.text
        
        if "INVALID_CONTENT" in result_text:
            return "INVALID", None
            
        usage = "N/A"
        if response.usage_metadata:
            u = response.usage_metadata
            usage = f"Input: {u.prompt_token_count} | Output: {u.candidates_token_count} | Total: {u.total_token_count}"
            
        return result_text, usage
        
    except Exception as e:
        st.error(f"Erro na análise inteligente: {e}")
        return None, None

def generate_image(prompt_visual, aspect_ratio):
    ar = "1:1"
    if "16:9" in aspect_ratio: ar = "16:9"
    elif "9:16" in aspect_ratio: ar = "9:16"

    try:
        response = client.models.generate_content(
            model=MODELO_IMAGEM_FIXO,
            contents=[types.Part.from_text(text=prompt_visual)],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=ar)
            )
        )
        for part in response.parts:
            if part.inline_data:
                return part.inline_data.data
        return None
    except Exception as e:
        st.error(f"Erro no Motor ({MODELO_IMAGEM_FIXO}): {e}")
        return None

# --- MODAL ---
@st.dialog("VISUALIZAÇÃO HD", width="large")
def show_full_image(image_bytes, token_info):
    img = Image.open(io.BytesIO(image_bytes))
    st.image(img, use_container_width=True)
    
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"resumo-grafico-heliosia-{ts}.png"
    
    col_dl, col_tok = st.columns([1, 1])
    with col_dl:
        st.download_button(
            label=f"⬇️ BAIXAR ({filename})",
            data=image_bytes,
            file_name=filename,
            mime="image/png",
            type="primary"
        )
    with col_tok:
        if token_info:
            st.markdown(f"<div class='token-box'>💎 CONSUMO DE INTELEGÊNCIA:<br>{token_info}</div>", unsafe_allow_html=True)

# --- UI ---
st.title("HELIOS // UNIVERSAL INFOGRAPHIC v2.4")

st.markdown(f"""
<div class="instruction-box">
    <strong>📘 MANUAL DE OPERAÇÃO UNIVERSAL:</strong>
    <ul>
        <li><strong>Qualquer Input:</strong> Suba Currículos, Textos ou <strong>FOTOS DE QUALQUER COISA</strong>.</li>
        <li><strong>Análise Inteligente:</strong> O sistema identifica se é um animal, objeto, lugar ou comida e adapta o infográfico.</li>
        <li><strong>Exemplo:</strong> Foto de um Gato -> Infográfico sobre a raça. Foto de um Tênis -> Infográfico técnico.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. INPUT UNIVERSAL")
    uploaded_file = st.file_uploader(
        "ARQUIVO (DOCS OU IMAGENS)", 
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"], 
        key=f"up_{reset_k}"
    )

    st.subheader(">> 2. CONFIGURAÇÃO")
    estilo_selecionado = st.selectbox("ESTILO VISUAL", list(ESTILOS.keys()), key=f"st_{reset_k}")
    formato_selecionado = st.selectbox("FORMATO", ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories)"], key=f"fmt_{reset_k}")
    
    st.subheader(">> 3. CONTEÚDO")
    idioma_selecionado = st.selectbox("IDIOMA", ["Português (Brasil)", "Inglês", "Espanhol", "Francês"], key=f"lang_{reset_k}")
    densidade_selecionada = st.selectbox("DENSIDADE", ["Conciso", "Padrão", "Detalhado (BETA)"], index=1, key=f"dens_{reset_k}")

with col2:
    st.subheader(">> 4. RESULTADO")
    preview_placeholder = st.empty()
    
    if st.session_state.last_image_bytes:
        img_preview = Image.open(io.BytesIO(st.session_state.last_image_bytes))
        preview_placeholder.image(img_preview, caption="PREVIEW (Clique abaixo para ampliar)", width=400)
        
        if st.button("🔍 AMPLIAR / DOWNLOAD", type="secondary", key=f"modal_btn_{reset_k}"):
            show_full_image(st.session_state.last_image_bytes, st.session_state.last_token_usage)

    pode_gerar = uploaded_file is not None and estilo_selecionado
    
    label_btn = "GERAR INFOGRÁFICO [RENDER]"
    if st.session_state.last_image_bytes:
        label_btn = "♻️ RE-GERAR (SUBSTITUIR ATUAL)"
    
    if st.button(label_btn, type="primary", disabled=not pode_gerar, key=f"btn_gen_{reset_k}"):
        if uploaded_file:
            preview_placeholder.empty()
            st.session_state.last_image_bytes = None
            
            with st.spinner(">> 1/3 CÉREBRO GEMINI: IDENTIFICANDO OBJETO/SER..."):
                content_part = process_uploaded_file(uploaded_file)
            
            if content_part:
                with st.spinner(f">> 2/3 CRIANDO ROTEIRO ({idioma_selecionado})..."):
                    prompt_otimizado, tokens = create_super_prompt(content_part, estilo_selecionado, idioma_selecionado, densidade_selecionada)
                
                if prompt_otimizado == "INVALID":
                    st.error("🚫 ERRO: Conteúdo não identificado. Certifique-se que o objeto/ser esteja visível.")
                elif prompt_otimizado:
                    with st.spinner(f">> 3/3 RENDERIZANDO PIXELS..."):
                        prompt_final = f"{prompt_otimizado} Style Details: {ESTILOS[estilo_selecionado]}"
                        img_bytes_raw = generate_image(prompt_final, formato_selecionado)
                        
                        if img_bytes_raw:
                            st.session_state.last_image_bytes = img_bytes_raw
                            st.session_state.last_token_usage = tokens
                            st.rerun()
