import streamlit as st
import os
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
    
    .instruction-box {
        border: 1px solid #333;
        background-color: #0a0a0a;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 5px solid #FFD700;
    }
    
    .beta-warning {
        color: #ff4b4b !important;
        font-size: 0.8em;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- MODELO HARDCODED (NANO BANANA PRO) ---
MODELO_IMAGEM_FIXO = "gemini-3-pro-image-preview" # Modelo nativo de imagem do Gemini

# --- GERENCIAMENTO DE ESTADO ---
if 'last_image_bytes' not in st.session_state:
    st.session_state.last_image_bytes = None
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

def reset_all():
    st.session_state.last_image_bytes = None
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

# Cliente Principal
client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

# --- FUNÇÕES ---
def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif "wordprocessingml" in uploaded_file.type:
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else: # txt
            text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None
    return text

def create_super_prompt(resume_text, style_name, idioma, densidade):
    # Lógica de Densidade para o Prompt
    instrucao_densidade = ""
    if densidade == "Conciso":
        instrucao_densidade = "Use MINIMAL TEXT. Focus heavily on icons, large headlines, and visual flow. Only key keywords. Do not use full sentences."
    elif densidade == "Detalhado (BETA)":
        instrucao_densidade = "Use HIGH TEXT DENSITY. Include detailed descriptions, full sentences where possible, and comprehensive lists. (WARNING: Ensure text remains legible)."
    else: # Padrão
        instrucao_densidade = "Use BALANCED TEXT and VISUALS. Use bullet points for achievements. Mix short descriptions with clear icons."

    prompt = f"""
    ROLE: You are a World-Class Art Director and Data Visualization Expert using Gemini Image Generation.
    TASK: Convert the resume below into a highly detailed, text-rich IMAGE GENERATION PROMPT.
    
    TARGET STYLE: {style_name}
    TARGET LANGUAGE FOR IMAGE TEXT: {idioma}
    INFORMATION DENSITY: {densidade}
    
    INSTRUCTIONS FOR THE PROMPT YOU WILL WRITE:
    1.  The output must be a single, long, descriptive prompt in English (but commanding the text inside the image to be in {idioma}).
    2.  Demand a "Text-Rich Infographic Layout".
    3.  **CRITICAL:** Explicitly instruction the model to render ALL visible text in {idioma}.
    4.  **DENSITY CONTROL:** {instrucao_densidade}
    5.  Explicitly ask to render the Candidate's Name as the Main Title.
    6.  Ask for a "Chronological Path" or "Timeline" visual structure.
    7.  Force the chosen style ({style_name}).
    8.  Demand "High fidelity text rendering", "Legible fonts".
    
    RESUME DATA:
    {resume_text[:8000]}
    
    OUTPUT: A raw prompt text. Start with: "A high-resolution, text-rich infographic poster in {style_name} style, text in {idioma}..."
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        return response.text
    except Exception as e:
        st.error(f"Erro na criação do prompt: {e}")
        return None

def generate_image(prompt_visual, aspect_ratio):
    ar = "1:1"
    if "16:9" in aspect_ratio: ar = "16:9"
    elif "9:16" in aspect_ratio: ar = "9:16"

    try:
        # Chamada NATIVA do Gemini para imagem
        response = client.models.generate_content(
            model=MODELO_IMAGEM_FIXO,
            contents=[prompt_visual],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=ar
                )
            )
        )
        for part in response.parts:
            if part.inline_data:
                return part.inline_data.data
        return None

    except Exception as e:
        st.error(f"Erro no Motor Nano Banana ({MODELO_IMAGEM_FIXO}): {e}")
        return None

# --- INTERFACE PRINCIPAL ---
st.title("HELIOS // RESUME INFOGRAPHIC")

st.markdown(f"""
<div class="instruction-box">
    <strong>📘 MANUAL DE OPERAÇÃO:</strong>
    <ul>
        <li><strong>Motor Ativo:</strong> <code>{MODELO_IMAGEM_FIXO}</code> (Nano Banana Pro).</li>
        <li><strong>Processo:</strong> Suba o arquivo -> Escolha Idioma/Densidade -> Clique em GERAR.</li>
        <li><strong>Nota:</strong> O modo "Detalhado" pode gerar erros de texto (alucinações de caracteres). Use com cautela.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns([1, 1])
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. UPLOAD DO CURRÍCULO")
    uploaded_file = st.file_uploader("ARQUIVO", type=["pdf", "docx", "txt"], key=f"up_{reset_k}")

    st.subheader(">> 2. CONFIGURAÇÃO VISUAL")
    estilo_selecionado = st.selectbox("ESTILO VISUAL", list(ESTILOS.keys()), key=f"st_{reset_k}")
    formato_selecionado = st.selectbox("FORMATO", ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories)"], key=f"fmt_{reset_k}")
    
    st.subheader(">> 3. CONTEÚDO")
    # Novos seletores de Idioma e Densidade
    idioma_selecionado = st.selectbox("IDIOMA DO INFOGRÁFICO", ["Português (Brasil)", "Inglês", "Espanhol", "Francês"], key=f"lang_{reset_k}")
    
    densidade_selecionada = st.selectbox("DENSIDADE DE INFORMAÇÃO", ["Conciso", "Padrão", "Detalhado (BETA)"], index=1, key=f"dens_{reset_k}")
    
    if "Detalhado" in densidade_selecionada:
        st.markdown("<p class='beta-warning'>⚠️ AVISO: Alta densidade aumenta o risco de erros de escrita na imagem.</p>", unsafe_allow_html=True)

with col2:
    st.subheader(">> 4. RENDERIZAÇÃO")
    image_placeholder = st.empty()
    
    if st.session_state.last_image_bytes:
        image = Image.open(io.BytesIO(st.session_state.last_image_bytes))
        image_placeholder.image(image, caption=f"INFOGRÁFICO ({MODELO_IMAGEM_FIXO})", use_container_width=True)
        
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        st.download_button("⬇️ BAIXAR (PNG)", data=buf.getvalue(), file_name="helios_resume.png", mime="image/png")
        st.info("Para gerar uma nova versão, clique em GERAR novamente.")

    pode_gerar = uploaded_file is not None and estilo_selecionado and formato_selecionado
    
    if st.button("GERAR INFOGRÁFICO [RENDER]", type="primary", disabled=not pode_gerar, key=f"btn_{reset_k}"):
        if uploaded_file:
            with st.spinner(">> 1/3 LENDO DOCUMENTO..."):
                texto_cv = extract_text_from_file(uploaded_file)
            
            if texto_cv:
                with st.spinner(f">> 2/3 DIREÇÃO DE ARTE ({idioma_selecionado.upper()})..."):
                    # Passamos os novos parâmetros para o criador de prompts
                    prompt_otimizado = create_super_prompt(texto_cv, estilo_selecionado, idioma_selecionado, densidade_selecionada)
                
                if prompt_otimizado:
                    with st.spinner(f">> 3/3 RENDERIZANDO NANO BANANA..."):
                        prompt_final = f"{prompt_otimizado} Style Details: {ESTILOS[estilo_selecionado]}"
                        
                        img_bytes_raw = generate_image(prompt_final, formato_selecionado)
                        
                        if img_bytes_raw:
                            st.session_state.last_image_bytes = img_bytes_raw
                            st.rerun()
