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
st.set_page_config(page_title="HELIOS | RESUME GEN", page_icon="🟡", layout="wide")

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
    
    /* Ajuste para o Modal */
    div[data-testid="stDialog"] {
        background-color: #000000;
        border: 2px solid #FFD700;
    }

    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- MODELO HARDCODED ---
MODELO_IMAGEM_FIXO = "gemini-3-pro-image-preview"

# --- GERENCIAMENTO DE ESTADO ---
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

# --- BASE DE ESTILOS ---
ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic illustration. A blend of intense action manga frames and vibrant, modern anime coloring. Settings should feature dramatic energy effects (speed lines, power auras, impact flashes), sharp angles, and highly expressive, dynamic character designs. Colors are intense and saturated (electric blues, fiery reds, deep purples). The atmosphere is intense, passionate, and empowering.",
    "3D NEUMORPHISM AESTHETIC": "Tactile 3D Neumorphism aesthetic illustration. A blend of modern UI design and satisfying, touchable digital objects. Settings should feature ultra-soft UI elements where shapes look extruded from the background using realistic soft shadows and light highlights. Finishes are glossy, frosted glass, or soft matte silicone. The color palette is clean and minimalist (off-whites, soft light grays, muted pastels). Shapes are inflated, puffy, and rounded.",
    "90s/Y2K PIXEL AESTHETIC": "90s/Y2K Retro Video Game aesthetic illustration. A blend of 16-bit pixel art and early internet culture design. Settings should feature bright neon or 'bubblegum' colors (hot pinks, electric blues, lime greens, bright yellows), chunky rounded typography, and pixelated icons. Apply a subtle CRT monitor scanline effect or slight digital glitch texture. The atmosphere is energetic, playful, loud, and radically nostalgic.",
    "WHITEBOARD ANIMATION": "Classic Whiteboard Animation aesthetic illustration. A blend of hand-drawn dry-erase marker sketches and direct visual storytelling. Settings should feature a clean bright white background with subtle marker residue smudges. Illustrations are done in standard marker colors (black, blue, red, green) with visible marker stroke textures. The hand drawing the elements should occasionally appear.",
    "MINI WORLD (DIORAMA)": "Isometric Miniature Diorama Aesthetic. A blend of playful voxel art and macro photography. The world looks like a tiny, living model kit. Settings should feature vibrant, saturated colors, soft 'toy-like' textures (matte plastic, clay, smooth wood), and distinct geometric shapes. Apply a 'tilt-shift' lens effect (blurred edges, sharp focus on the subject) to exaggerate the small scale.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography combined with a high-end modern lifestyle aesthetic. Settings should feature contemporary, sophisticated interior design with minimalist decor and clean lines. Use soft natural lighting to create a cozy yet polished atmosphere. Focus on sharp details, realistic textures, deep depth of field.",
    "RETRO-FUTURISM": "Nostalgic Retro Futurism Aesthetic photography illustration. A blend of comforting 90s sci-fi warmth and modern digital sharpness. Settings should feature neon lighting (teals, deep purples, warm oranges), chrome surfaces reflecting the environment, and subtle technological overlays. Apply a cinematic film grain or mild VHS texture to create a 'memory' feel.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast Aesthetic photography illustration. The visual focus is on massive, heavy typography and brutalist geometric shapes. Use a strict Black & White palette with one single vibrant neon accent color (e.g., Acid Green or Electric Blue). Lighting should be high-contrast 'noir' style (hard silhouettes, spotlighting). The text itself acts as the main visual element. The atmosphere is urgent, impactful, and bold."
}

# --- SIDEBAR & AUTH ---
with st.sidebar:
    st.title("🟡 HELIOS")
    st.markdown("**RESUME INFOGRAPHIC GEN**")
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
    """
    Processa tanto Texto (PDF/DOCX/TXT) quanto Imagens (JPG/PNG).
    Retorna um objeto Part do Gemini pronto para envio.
    """
    try:
        # Caso 1: Imagens (Visão Computacional)
        if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
            return types.Part.from_bytes(uploaded_file.getvalue(), mime_type=uploaded_file.type)
        
        # Caso 2: Documentos de Texto
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
            
        return types.Part.from_text(text=text_content[:15000]) # Limite seguro de caracteres

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return None

def create_super_prompt(content_part, style_name, idioma, densidade):
    # Prompt ajustado para aceitar Imagem ou Texto
    instrucao_densidade = ""
    if densidade == "Conciso":
        instrucao_densidade = "Use MINIMAL TEXT. Focus heavily on icons, large headlines, and visual flow. Only key keywords. Do not use full sentences."
    elif densidade == "Detalhado (BETA)":
        instrucao_densidade = "Use HIGH TEXT DENSITY. Include detailed descriptions. (WARNING: Ensure text remains legible)."
    else:
        instrucao_densidade = "Use BALANCED TEXT and VISUALS. Use bullet points. Mix short descriptions with clear icons."

    prompt_text = f"""
    ROLE: You are a World-Class Art Director and Data Visualization Expert using Gemini Image Generation.
    TASK: Analyze the provided content (Text or Image) and convert it into a highly detailed IMAGE GENERATION PROMPT.
    
    TARGET STYLE: {style_name}
    TARGET LANGUAGE FOR IMAGE TEXT: {idioma}
    INFORMATION DENSITY: {densidade}
    
    INSTRUCTIONS FOR THE PROMPT YOU WILL WRITE:
    1.  Output a single, long, descriptive prompt in English commanding the text inside the image to be in {idioma}.
    2.  If the input is a resume: Create a career timeline infographic.
    3.  If the input is an image/diagram: Recreate the concept as a polished infographic in the chosen style.
    4.  **CRITICAL:** Render ALL visible text in {idioma}.
    5.  **DENSITY CONTROL:** {instrucao_densidade}
    6.  Force the chosen style ({style_name}).
    
    OUTPUT START: "A high-resolution, text-rich infographic poster in {style_name} style, text in {idioma}..."
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                types.Part.from_text(prompt_text),
                content_part # Aqui entra o Texto ou a Imagem
            ]
        )
        
        # Captura Token Usage se disponível
        usage = "N/A"
        if response.usage_metadata:
            u = response.usage_metadata
            usage = f"Input: {u.prompt_token_count} | Output: {u.candidates_token_count} | Total: {u.total_token_count}"
            
        return response.text, usage
        
    except Exception as e:
        st.error(f"Erro na análise: {e}")
        return None, None

def generate_image(prompt_visual, aspect_ratio):
    ar = "1:1"
    if "16:9" in aspect_ratio: ar = "16:9"
    elif "9:16" in aspect_ratio: ar = "9:16"

    try:
        response = client.models.generate_content(
            model=MODELO_IMAGEM_FIXO,
            contents=[prompt_visual],
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

# --- MODAL DE VISUALIZAÇÃO ---
@st.dialog("VISUALIZAÇÃO EM ALTA RESOLUÇÃO", width="large")
def show_full_image(image_bytes, token_info):
    img = Image.open(io.BytesIO(image_bytes))
    st.image(img, use_container_width=True)
    
    # Nome do Arquivo com Timestamp
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"resumo-grafico-heliosia-{ts}.png"
    
    col_dl, col_tok = st.columns([1, 1])
    with col_dl:
        st.download_button(
            label=f"⬇️ BAIXAR ARQUIVO ({filename})",
            data=image_bytes,
            file_name=filename,
            mime="image/png",
            type="primary"
        )
    with col_tok:
        if token_info:
            st.markdown(f"<div class='token-box'>💎 CUSTO DE ANÁLISE (TOKENS):<br>{token_info}</div>", unsafe_allow_html=True)

# --- INTERFACE PRINCIPAL ---
st.title("HELIOS // RESUME INFOGRAPHIC v2.2")

st.markdown(f"""
<div class="instruction-box">
    <strong>📘 MANUAL DE OPERAÇÃO:</strong>
    <ul>
        <li><strong>Inputs:</strong> Aceita PDF, DOCX, TXT e <strong>IMAGENS (JPG/PNG até 10MB)</strong>.</li>
        <li><strong>Motor:</strong> <code>{MODELO_IMAGEM_FIXO}</code> (Nano Banana Pro).</li>
        <li><strong>Nota:</strong> Se já houver imagem gerada, clique em GERAR para substituir (sem aviso prévio).</li>
    </ul>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. INPUT (TEXTO OU IMAGEM)")
    # Aceita Imagens agora
    uploaded_file = st.file_uploader(
        "ARQUIVO FONTE", 
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png"], 
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
    
    # Se existe imagem no estado, mostra PREVIEW
    if st.session_state.last_image_bytes:
        img_preview = Image.open(io.BytesIO(st.session_state.last_image_bytes))
        # Mostra menor (width=400) para caber na tela
        preview_placeholder.image(img_preview, caption="PREVIEW (Clique abaixo para ampliar)", width=400)
        
        # Botão para abrir o Modal
        if st.button("🔍 AMPLIAR / DOWNLOAD", type="secondary", key=f"modal_btn_{reset_k}"):
            show_full_image(st.session_state.last_image_bytes, st.session_state.last_token_usage)

    # Lógica de Geração
    pode_gerar = uploaded_file is not None and estilo_selecionado
    
    label_btn = "GERAR INFOGRÁFICO [RENDER]"
    if st.session_state.last_image_bytes:
        label_btn = "♻️ RE-GERAR (SUBSTITUIR ATUAL)"
    
    if st.button(label_btn, type="primary", disabled=not pode_gerar, key=f"btn_gen_{reset_k}"):
        if uploaded_file:
            # Limpa preview anterior visualmente
            preview_placeholder.empty()
            st.session_state.last_image_bytes = None
            
            with st.spinner(">> 1/3 PROCESSANDO INPUT (VISÃO/TEXTO)..."):
                content_part = process_uploaded_file(uploaded_file)
            
            if content_part:
                with st.spinner(f">> 2/3 DIREÇÃO DE ARTE ({idioma_selecionado})..."):
                    prompt_otimizado, tokens = create_super_prompt(content_part, estilo_selecionado, idioma_selecionado, densidade_selecionada)
                
                if prompt_otimizado:
                    with st.spinner(f">> 3/3 RENDERIZANDO PIXELS..."):
                        prompt_final = f"{prompt_otimizado} Style Details: {ESTILOS[estilo_selecionado]}"
                        img_bytes_raw = generate_image(prompt_final, formato_selecionado)
                        
                        if img_bytes_raw:
                            st.session_state.last_image_bytes = img_bytes_raw
                            st.session_state.last_token_usage = tokens
                            st.rerun() # Recarrega para exibir o novo preview
