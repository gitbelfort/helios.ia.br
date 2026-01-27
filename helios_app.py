import streamlit as st
import os
from google import genai
from google.genai.types import Content, Part
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
    
    .stTextInput, .stSelectbox, .stFileUploader { color: #FFD700; }
    .stSelectbox > div > div { background-color: #111; color: #FFD700; border: 1px solid #FFD700; }
    
    .stButton > button { 
        background-color: #000000; color: #FFD700; border: 2px solid #FFD700; 
        border-radius: 0px; text-transform: uppercase; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 20px #FFD700; }
    
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    [data-testid='stFileUploader'] { border: 1px dashed #FFD700; padding: 20px; background-color: #050505; }
    .helios-box { border: 1px solid #FFD700; padding: 20px; background-color: #050505; border-left: 5px solid #FFD700; margin-top: 10px; }
    
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- BASE DE ESTILOS ---
ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic. Intense action manga frames, vibrant anime coloring. Dramatic energy effects, sharp angles. Colors: electric blues, fiery reds. Atmosphere: intense, empowering.",
    "3D NEUMORPHISM": "Tactile 3D Neumorphism. Modern UI design, satisfying touchable digital objects. Soft UI elements, extruded shapes, realistic soft shadows. Finishes: glossy, frosted glass. Clean, minimalist palette. Atmosphere: clean, soothing.",
    "90s/Y2K PIXEL": "90s/Y2K Retro Video Game aesthetic. 16-bit pixel art, early internet design. Bright neon 'bubblegum' colors, chunky rounded typography, pixelated icons. Subtle CRT scanline effect. Atmosphere: energetic, playful, nostalgic.",
    "WHITEBOARD ANIMATION": "Classic Whiteboard Animation. Hand-drawn dry-erase marker sketches. Clean bright white background, marker residue smudges. Standard marker colors (black, blue, red, green). Educational tone.",
    "MINI WORLD (DIORAMA)": "Isometric Miniature Diorama. Playful voxel art meets macro photography. Tiny, living model kit look. Vibrant colors, soft 'toy-like' textures (matte plastic, clay). Tilt-shift effect. Atmosphere: charming, tactile.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography. Modern lifestyle aesthetic. Sophisticated interior design, minimalist decor. Soft natural lighting. Sharp details, realistic textures. Professional atmosphere.",
    "RETRO-FUTURISM": "Nostalgic Retro Futurism. 90s sci-fi warmth meets modern digital sharpness. Neon lighting (teals, purples), chrome surfaces. Cinematic film grain, mild VHS texture. Atmosphere: dreamy, exciting.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast. Focus on massive, heavy typography and brutalist shapes. Black & White palette with one neon accent (Acid Green). High-contrast 'noir' lighting. Atmosphere: urgent, impactful."
}

# --- SIDEBAR ---
with st.sidebar:
    st.title("🟡 HELIOS")
    st.markdown("**RESUME INFOGRAPHIC GEN**")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    st.markdown("---")
    st.info("SISTEMA ONLINE\nDOMÍNIO: HELIOS.IA.BR")

if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

# --- CONFIGURAÇÃO CLIENTE ---
try:
    # Mantemos v1beta pois é onde o Imagen costuma habitar
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

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

def summarize_career(resume_text):
    prompt = """
    You are an expert Infographic Designer. Analyze the resume below.
    Extract key career milestones, roles, and skills.
    
    OUTPUT GOAL: Create a visual description prompt for an image generator.
    Do NOT output the resume text. Output a descriptive PROMPT in English.
    
    Structure:
    "An infographic layout showing a career timeline. Key milestones: [List 3-4 major roles]. Theme: Professional growth in [Industry]. Icons representing skills: [List skills]. Visual flow from [Start Date] to [End Date]. Text elements are minimal and bold."
    
    Resume:
    """ + resume_text[:6000]
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        return response.text
    except Exception as e:
        st.error(f"Erro na análise: {e}")
        return None

def generate_image(prompt_visual, style_name, style_desc, aspect_ratio):
    # Prompt Refinado
    full_prompt = (
        f"Create a professional infographic image in {style_name} style. "
        f"{style_desc} "
        f"The content depicts: {prompt_visual}. "
        f"High resolution, detailed, clean text layout representation, 8k, infographic design."
    )
    
    ar_param = "1:1"
    if "16:9" in aspect_ratio: ar_param = "16:9"
    elif "9:16" in aspect_ratio: ar_param = "9:16"

    # TENTATIVA 1: IMAGEN 3 (Nano Banana Pro)
    try:
        # print("Tentando Imagen 3...")
        response = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=full_prompt,
            config={'aspect_ratio': ar_param}
        )
        return response.generated_images[0].image, "NANO BANANA PRO (IMAGEN 3)"
        
    except Exception as e:
        # TENTATIVA 2: IMAGEN 2 (Fallback Robusto)
        # print(f"Imagen 3 falhou ({e}), tentando Imagen 2...")
        try:
            response = client.models.generate_images(
                model='imagen-2.0-generate-001',
                prompt=full_prompt,
                config={'aspect_ratio': ar_param}
            )
            return response.generated_images[0].image, "IMAGEN 2 (COMPATIBILIDADE)"
        except Exception as e2:
            st.error(f"Erro Fatal (Todos os modelos falharam): {e2}")
            return None, "ERRO"

# --- INTERFACE ---
st.title("HELIOS // RESUME INFOGRAPHIC")
st.markdown("`[MOTOR: NANO BANANA PRO (AUTO-FALLBACK)]`")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(">> 1. UPLOAD DO CURRÍCULO")
    uploaded_file = st.file_uploader("ARQUIVO", type=["pdf", "docx", "txt"])

    st.subheader(">> 2. CONFIGURAÇÃO VISUAL")
    estilo_selecionado = st.selectbox("ESTILO VISUAL", list(ESTILOS.keys()))
    formato_selecionado = st.selectbox("FORMATO", ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories)"])
    st.caption(f"📝 {ESTILOS[estilo_selecionado][:100]}...")

with col2:
    st.subheader(">> 3. GERAÇÃO")
    image_placeholder = st.empty()
    
    if uploaded_file and st.button("GERAR INFOGRÁFICO [RENDER]", type="primary"):
        with st.spinner(">> 1/3 LENDO DADOS..."):
            texto_cv = extract_text_from_file(uploaded_file)
        
        if texto_cv:
            with st.spinner(">> 2/3 CRIANDO ROTEIRO VISUAL..."):
                resumo_visual = summarize_career(texto_cv)
            
            if resumo_visual:
                with st.spinner(f">> 3/3 RENDERIZANDO (Tentando Imagen 3...)..."):
                    img_bytes, modelo_usado = generate_image(resumo_visual, estilo_selecionado, ESTILOS[estilo_selecionado], formato_selecionado)
                    
                    if img_bytes:
                        image = Image.open(io.BytesIO(img_bytes.image_bytes))
                        image_placeholder.image(image, caption=f"INFOGRÁFICO GERADO VIA {modelo_usado}", use_container_width=True)
                        
                        buf = io.BytesIO()
                        image.save(buf, format="PNG")
                        st.download_button("⬇️ BAIXAR (PNG)", data=buf.getvalue(), file_name="helios_resume.png", mime="image/png")
                        
                        if "IMAGEN 3" in modelo_usado:
                            st.success(">> SUCESSO: Renderizado com NANO BANANA PRO.")
                        else:
                            st.warning(f">> AVISO: Nano Banana Pro (v3) indisponível na sua chave. Renderizado com {modelo_usado}.")
