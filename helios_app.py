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
    
    /* Inputs e Selectbox */
    .stTextInput, .stSelectbox, .stFileUploader {
        color: #FFD700;
    }
    .stSelectbox > div > div {
        background-color: #111; color: #FFD700; border: 1px solid #FFD700;
    }
    
    /* Botões */
    .stButton > button { 
        background-color: #000000; color: #FFD700; border: 2px solid #FFD700; 
        border-radius: 0px; text-transform: uppercase; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton > button:hover { 
        background-color: #FFD700; color: #000000; box-shadow: 0 0 20px #FFD700; 
    }
    
    /* Texto */
    h1, h2, h3, p, label, span, div { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    /* Área de Upload */
    [data-testid='stFileUploader'] {
        border: 1px dashed #FFD700;
        padding: 20px;
        background-color: #050505;
    }
    
    /* Box de Resultado */
    .helios-box { 
        border: 1px solid #FFD700; padding: 20px; 
        background-color: #050505; border-left: 5px solid #FFD700; margin-top: 10px; 
    }
    
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- BASE DE ESTILOS (Do arquivo ESTILOS.txt) ---
ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic illustration. A blend of intense action manga frames and vibrant, modern anime coloring. Settings should feature dramatic energy effects (speed lines, power auras, impact flashes), sharp angles, and highly expressive, dynamic character designs. Colors are intense and saturated (electric blues, fiery reds, deep purples). Apply effects like 'impact frames' or sudden shifts in color palette to emphasize key points. The atmosphere is intense, passionate, and empowering.",
    "3D NEUMORPHISM AESTHETIC": "Tactile 3D Neumorphism aesthetic illustration. A blend of modern UI design and satisfying, touchable digital objects. Settings should feature ultra-soft UI elements where shapes look extruded from the background using realistic soft shadows and light highlights. Finishes are glossy, frosted glass, or soft matte silicone. The color palette is clean and minimalist. Shapes are inflated, puffy, and rounded. The atmosphere is clean, soothing, highly organized.",
    "90s/Y2K PIXEL AESTHETIC": "90s/Y2K Retro Video Game aesthetic illustration. A blend of 16-bit pixel art and early internet culture design. Settings should feature bright neon or 'bubblegum' colors (hot pinks, electric blues, lime greens, bright yellows), chunky rounded typography, and pixelated icons. Apply a subtle CRT monitor scanline effect or slight digital glitch texture. The atmosphere is energetic, playful, loud, and radically nostalgic.",
    "WHITEBOARD ANIMATION": "Classic Whiteboard Animation aesthetic illustration. A blend of hand-drawn dry-erase marker sketches and direct visual storytelling. Settings should feature a clean bright white background with subtle marker residue smudges. Illustrations are done in standard marker colors (black, blue, red, green) with visible marker stroke textures. The hand drawing the elements should occasionally appear.",
    "KAWAII DOODLE ART": "Hand-Drawn Kawaii Doodle Art aesthetic illustration. A blend of charming sketchbook drawings and cheerful simplicity. Settings should feature soft pastel color palettes, textured paper backgrounds (lined notebook paper), and thick, imperfect marker-pen outlines. Apply a subtle crayon texture to fills. The atmosphere is whimsical, sweet, cozy, and innocent.",
    "MINI WORLD AESTHETIC": "Isometric Miniature Diorama Aesthetic. A blend of playful voxel art and macro photography. The world looks like a tiny, living model kit. Settings should feature vibrant, saturated colors, soft 'toy-like' textures (matte plastic, clay, smooth wood), and distinct geometric shapes. Apply a 'tilt-shift' lens effect to exaggerate the small scale.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography combined with a high-end modern lifestyle aesthetic. Settings should feature contemporary, sophisticated interior design with minimalist decor and clean lines. Use soft natural lighting to create a cozy yet polished atmosphere. Focus on sharp details, realistic textures, deep depth of field.",
    "RETRO-FUTURISM": "Nostalgic Retro Futurism Aesthetic photography illustration. A blend of comforting 90s sci-fi warmth and modern digital sharpness. Settings should feature neon lighting (teals, deep purples, warm oranges), chrome surfaces reflecting the environment, and subtle technological overlays. Apply a cinematic film grain or mild VHS texture.",
    "HUMAN TOUCH": "The Human Touch Aesthetic. Visuals should feel handcrafted, raw, and authentic (Intentional Imperfection). Settings should resemble a creative studio or a messy but cozy workspace with natural sunlight and harsh, realistic shadows. Use mixed media elements: paper textures, hand-drawn overlays, and stop-motion feel.",
    "MULTI-DIMENSIONAL": "Multi-Dimensional Immersive Aesthetic (2D mixed with 3D). Settings should feature depth-defying elements where 3D objects interact with flat 2D graphic layers. Use volumetric lighting to create a sense of space. Elements should appear to 'pop out' of the screen using parallax effects. The atmosphere is tech-savvy and dynamic.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast Aesthetic. The visual focus is on massive, heavy typography and brutalist geometric shapes. Use a strict Black & White palette with one single vibrant neon accent color (e.g., Acid Green). Lighting should be high-contrast 'noir' style. The text itself acts as the main visual element. The atmosphere is urgent, impactful, and bold."
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

# Configuração do Cliente
try:
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# --- FUNÇÕES DE EXTRAÇÃO ---
def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else: # txt
            text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None
    return text

# --- FUNÇÃO LLM (RESUMIR CURRÍCULO) ---
def summarize_career(resume_text):
    prompt = """
    Você é um especialista em Design de Infográficos e Carreira.
    Analise o currículo abaixo e extraia os principais marcos da carreira (Timeline), cargos, habilidades chave e conquistas.
    
    O objetivo é criar um Prompt Visual para gerar um infográfico.
    Não responda com o resumo em texto para ler. Responda com um PROMPT DE IMAGEM em Inglês detalhado, descrevendo visualmente como o infográfico deve ser.
    
    Estrutura do Prompt de Saída (em Inglês):
    "An infographic visualization showing a career journey timeline. Key milestones include: [List milestones visually]. The central theme represents a professional in [Area]. Include visual icons representing skills like [Skills]. The layout shows progression from [Start] to [Current]."
    
    Currículo:
    """ + resume_text[:5000] # Limita caracteres para não estourar token
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        return response.text
    except Exception as e:
        st.error(f"Erro na análise do currículo: {e}")
        return None

# --- FUNÇÃO IMAGEN (GERAR INFOGRÁFICO) ---
def generate_image(prompt_visual, style_name, style_desc, aspect_ratio):
    # Constrói o Prompt Final Poderoso
    full_prompt = (
        f"Create a high-quality infographic in a {style_name} style. "
        f"{style_desc} "
        f"Content details: {prompt_visual}. "
        f"Ensure high resolution, 2k, detailed, professional layout, infographic design."
    )
    
    # Mapeamento de Aspect Ratio para Imagen 3
    # Imagen 3 usa strings como '1:1', '16:9', etc.
    if aspect_ratio == "1:1 (Quadrado)":
        ar_param = "1:1"
    elif aspect_ratio == "16:9 (Paisagem)":
        ar_param = "16:9"
    else: # 9:16
        ar_param = "9:16"

    try:
        # Chamada para Imagen 3 via google-genai
        response = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=full_prompt,
            config={'aspect_ratio': ar_param}
        )
        return response.generated_images[0].image
    except Exception as e:
        st.error(f"Erro na geração da imagem (Nano Banana Pro): {e}")
        return None

# --- INTERFACE PRINCIPAL ---

st.title("HELIOS // RESUME INFOGRAPHIC")
st.markdown("`[MOTOR: NANO BANANA PRO + GEMINI PRO]`")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(">> 1. UPLOAD DO CURRÍCULO")
    uploaded_file = st.file_uploader("ARQUIVO (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

    st.subheader(">> 2. CONFIGURAÇÃO VISUAL")
    estilo_selecionado = st.selectbox("ESTILO VISUAL (ESTILOS.txt)", list(ESTILOS.keys()))
    
    formato_selecionado = st.selectbox(
        "FORMATO DA IMAGEM", 
        ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories/Vertical)"]
    )
    
    # Mostra descrição do estilo escolhido
    st.caption(f"📝 DETALHES DO ESTILO: {ESTILOS[estilo_selecionado][:150]}...")

with col2:
    st.subheader(">> 3. GERAÇÃO")
    
    # Placeholder para a imagem
    image_placeholder = st.empty()
    
    if uploaded_file is not None:
        btn_gerar = st.button("GERAR INFOGRÁFICO [RENDER]", type="primary")
        
        if btn_gerar:
            with st.spinner(">> 1/3 LENDO DADOS..."):
                texto_cv = extract_text_from_file(uploaded_file)
            
            if texto_cv:
                with st.spinner(">> 2/3 ANALISANDO CARREIRA (GEMINI PRO)..."):
                    resumo_visual = summarize_career(texto_cv)
                
                if resumo_visual:
                    with st.spinner(f">> 3/3 RENDERIZANDO ESTILO {estilo_selecionado}..."):
                        img_bytes = generate_image(
                            resumo_visual, 
                            estilo_selecionado, 
                            ESTILOS[estilo_selecionado],
                            formato_selecionado
                        )
                        
                        if img_bytes:
                            # Converte bytes para PIL Image para exibir e salvar
                            image = Image.open(io.BytesIO(img_bytes.image_bytes))
                            image_placeholder.image(image, caption="INFOGRÁFICO GERADO", use_container_width=True)
                            
                            # Botão de Download
                            buf = io.BytesIO()
                            image.save(buf, format="PNG")
                            st.download_button(
                                label="⬇️ BAIXAR IMAGEM (2K)",
                                data=buf.getvalue(),
                                file_name="helios_resume.png",
                                mime="image/png"
                            )
                            st.success(">> GERAÇÃO CONCLUÍDA.")
    else:
        st.info("AGUARDANDO ARQUIVO...")
        image_placeholder.markdown(
            """
            <div style='border: 1px dashed #FFD700; height: 300px; display: flex; align-items: center; justify-content: center; color: #555;'>
            [ÁREA DE RENDERIZAÇÃO]
            </div>
            """, 
            unsafe_allow_html=True
        )
