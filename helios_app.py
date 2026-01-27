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
    
    /* Estilo para a descrição completa */
    .style-desc {
        font-size: 0.9em;
        color: #aaa !important;
        background-color: #111;
        padding: 10px;
        border: 1px solid #333;
        margin-bottom: 20px;
    }
    
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- BASE DE ESTILOS ---
ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic illustration. A blend of intense action manga frames and vibrant, modern anime coloring. Settings should feature dramatic energy effects (speed lines, power auras, impact flashes), sharp angles, and highly expressive, dynamic character designs. Colors are intense and saturated (electric blues, fiery reds, deep purples). Apply effects like 'impact frames' or sudden shifts in color palette to emphasize key points. The atmosphere is intense, passionate, and empowering.",
    "3D NEUMORPHISM": "Tactile 3D Neumorphism aesthetic illustration. A blend of modern UI design and satisfying, touchable digital objects. Settings should feature ultra-soft UI elements where shapes look extruded from the background using realistic soft shadows and light highlights. Finishes are glossy, frosted glass, or soft matte silicone. The color palette is clean and minimalist (off-whites, soft light grays, muted pastels). Shapes are inflated, puffy, and rounded. The atmosphere is clean, soothing, highly organized.",
    "90s/Y2K PIXEL": "90s/Y2K Retro Video Game aesthetic illustration. A blend of 16-bit pixel art and early internet culture design. Settings should feature bright neon or 'bubblegum' colors (hot pinks, electric blues, lime greens, bright yellows), chunky rounded typography, and pixelated icons. Apply a subtle CRT monitor scanline effect or slight digital glitch texture. The atmosphere is energetic, playful, loud, and radically nostalgic.",
    "WHITEBOARD ANIMATION": "Classic Whiteboard Animation aesthetic illustration. A blend of hand-drawn dry-erase marker sketches and direct visual storytelling. Settings should feature a clean bright white background with subtle marker residue smudges. Illustrations are done in standard marker colors (black, blue, red, green) with visible marker stroke textures. The hand drawing the elements should occasionally appear. The atmosphere is clear, direct, educational.",
    "MINI WORLD (DIORAMA)": "Isometric Miniature Diorama Aesthetic. A blend of playful voxel art and macro photography. The world looks like a tiny, living model kit. Settings should feature vibrant, saturated colors, soft 'toy-like' textures (matte plastic, clay, smooth wood), and distinct geometric shapes. Apply a 'tilt-shift' lens effect (blurred edges, sharp focus on the subject) to exaggerate the small scale. The atmosphere is charming, tactile, and delightful.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography combined with a high-end modern lifestyle aesthetic. Settings should feature contemporary, sophisticated interior design with minimalist decor and clean lines. Use soft natural lighting to create a cozy yet polished atmosphere. Focus on sharp details, realistic textures, deep depth of field. Explanatory, didactic, and inspiring tone.",
    "RETRO-FUTURISM": "Nostalgic Retro Futurism Aesthetic photography illustration. A blend of comforting 90s sci-fi warmth and modern digital sharpness. Settings should feature neon lighting (teals, deep purples, warm oranges), chrome surfaces reflecting the environment, and subtle technological overlays. Apply a cinematic film grain or mild VHS texture to create a 'memory' feel. The atmosphere is dreamy, hazy, and exciting.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast Aesthetic photography illustration. The visual focus is on massive, heavy typography and brutalist geometric shapes. Use a strict Black & White palette with one single vibrant neon accent color (e.g., Acid Green or Electric Blue). Lighting should be high-contrast 'noir' style (hard silhouettes, spotlighting). The text itself acts as the main visual element. The atmosphere is urgent, impactful, and bold."
}

# --- SIDEBAR ---
with st.sidebar:
    st.title("🟡 HELIOS")
    st.markdown("**RESUME INFOGRAPHIC GEN**")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    
    st.markdown("---")
    st.markdown("### 🛠️ DIAGNÓSTICO")
    if st.button("LISTAR MODELOS DISPONÍVEIS"):
        if not api_key:
            st.error("Insira a API Key primeiro.")
        else:
            try:
                client_debug = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
                # Tenta listar os modelos (comando padrão da nova SDK)
                # Nota: A estrutura de resposta pode variar, vamos tentar imprimir o bruto
                models = client_debug.models.list()
                
                lista_nomes = []
                for m in models:
                    # Filtra apenas modelos 'imagen' para facilitar a leitura
                    if 'imagen' in m.name:
                        lista_nomes.append(m.name)
                
                if lista_nomes:
                    st.success("Modelos de Imagem Encontrados:")
                    st.code("\n".join(lista_nomes))
                else:
                    st.warning("Nenhum modelo 'imagen' encontrado explicitamente na lista.")
                    # Mostra tudo se não achar imagen
                    all_models = [m.name for m in models]
                    st.code("\n".join(all_models))
                    
            except Exception as e:
                st.error(f"Erro ao listar: {e}")

    st.markdown("---")
    st.info("DOMÍNIO: HELIOS.IA.BR")

if not api_key:
    st.warning(">> ALERTA: INSIRA A CHAVE DE ACESSO PARA INICIAR.")
    st.stop()

# --- CLIENTE ---
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

def generate_image(prompt_visual, style_name, style_desc, aspect_ratio, model_name):
    full_prompt = (
        f"Create a professional infographic image in {style_name} style. "
        f"{style_desc} "
        f"The content depicts: {prompt_visual}. "
        f"High resolution, detailed, clean text layout representation, 8k, infographic design."
    )
    
    ar_param = "1:1"
    if "16:9" in aspect_ratio: ar_param = "16:9"
    elif "9:16" in aspect_ratio: ar_param = "9:16"

    try:
        response = client.models.generate_images(
            model=model_name,
            prompt=full_prompt,
            config={'aspect_ratio': ar_param}
        )
        return response.generated_images[0].image
    except Exception as e:
        st.error(f"Erro no Modelo {model_name}: {e}")
        return None

# --- INTERFACE PRINCIPAL ---
st.title("HELIOS // RESUME INFOGRAPHIC")
st.markdown("`[MOTOR: SELEÇÃO MANUAL]`")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(">> 1. UPLOAD DO CURRÍCULO")
    uploaded_file = st.file_uploader("ARQUIVO", type=["pdf", "docx", "txt"])

    st.subheader(">> 2. CONFIGURAÇÃO VISUAL")
    
    # 1. Estilo
    estilo_selecionado = st.selectbox("ESTILO VISUAL", list(ESTILOS.keys()))
    # Descrição Completa
    st.markdown(f"<div class='style-desc'>{ESTILOS[estilo_selecionado]}</div>", unsafe_allow_html=True)
    
    # 2. Formato
    formato_selecionado = st.selectbox("FORMATO", ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories)"])
    
    # 3. Modelo (Manual)
    st.subheader(">> 3. SELEÇÃO DO MOTOR")
    modelo_selecionado = st.selectbox(
        "MODELO DE GERAÇÃO (IMAGEN)", 
        [
            "imagen-3.0-generate-001",
            "imagen-2.0-generate-001"
        ],
        index=0 # Padrão v3
    )
    st.caption("Se o v3 der erro 404, selecione o v2 ou use o botão de diagnóstico na barra lateral.")

with col2:
    st.subheader(">> 4. GERAÇÃO")
    image_placeholder = st.empty()
    
    # Verifica se tudo está preenchido
    pode_gerar = uploaded_file is not None and estilo_selecionado and formato_selecionado and modelo_selecionado
    
    if st.button("GERAR INFOGRÁFICO [RENDER]", type="primary", disabled=not pode_gerar):
        if uploaded_file:
            with st.spinner(">> 1/3 LENDO DADOS..."):
                texto_cv = extract_text_from_file(uploaded_file)
            
            if texto_cv:
                with st.spinner(">> 2/3 CRIANDO ROTEIRO VISUAL..."):
                    resumo_visual = summarize_career(texto_cv)
                
                if resumo_visual:
                    with st.spinner(f">> 3/3 RENDERIZANDO COM {modelo_selecionado}..."):
                        img_bytes = generate_image(
                            resumo_visual, 
                            estilo_selecionado, 
                            ESTILOS[estilo_selecionado], 
                            formato_selecionado,
                            modelo_selecionado
                        )
                        
                        if img_bytes:
                            image = Image.open(io.BytesIO(img_bytes.image_bytes))
                            image_placeholder.image(image, caption=f"INFOGRÁFICO ({modelo_selecionado})", use_container_width=True)
                            
                            buf = io.BytesIO()
                            image.save(buf, format="PNG")
                            st.download_button("⬇️ BAIXAR (PNG)", data=buf.getvalue(), file_name="helios_resume.png", mime="image/png")
                            st.success("SUCESSO.")
    
    if not pode_gerar:
        st.info("Preencha todos os campos para habilitar a geração.")
