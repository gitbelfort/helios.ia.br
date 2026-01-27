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
    
    /* Fontes e Cores */
    h1, h2, h3, p, label, span, div, li { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    /* Inputs */
    .stTextInput, .stSelectbox, .stFileUploader { color: #FFD700; }
    .stSelectbox > div > div { background-color: #111; color: #FFD700; border: 1px solid #FFD700; }
    
    /* Botões */
    .stButton > button { 
        background-color: #000000; color: #FFD700; border: 2px solid #FFD700; 
        border-radius: 0px; text-transform: uppercase; transition: 0.3s; width: 100%; font-weight: bold; font-size: 1.1em;
    }
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 20px #FFD700; }
    
    /* Área de Upload */
    [data-testid='stFileUploader'] { border: 1px dashed #FFD700; padding: 20px; background-color: #050505; }
    
    /* Caixas de Instrução */
    .instruction-box {
        border: 1px solid #333;
        background-color: #0a0a0a;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 5px solid #FFD700;
    }
    
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE ESTADO (Persistência) ---
if 'last_image_bytes' not in st.session_state:
    st.session_state.last_image_bytes = None
if 'last_model_used' not in st.session_state:
    st.session_state.last_model_used = None
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

def reset_all():
    """Limpa tudo para uma nova geração"""
    st.session_state.last_image_bytes = None
    st.session_state.last_model_used = None
    st.session_state.reset_trigger += 1

# --- BASE DE ESTILOS (PROMPTS OTIMIZADOS) ---
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

# --- FETCH DINÂMICO DE MODELOS ---
@st.cache_data(show_spinner=False)
def get_available_models(key):
    try:
        temp_client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
        all_models = temp_client.models.list()
        imagen_models = []
        for m in all_models:
            if "imagen" in m.name.lower():
                clean_name = m.name.replace("models/", "")
                imagen_models.append(clean_name)
        # Tenta ordenar para deixar os mais novos/ultra no topo
        imagen_models.sort(reverse=True)
        return imagen_models
    except Exception as e:
        return [f"ERRO: {str(e)}"]

available_imagen_models = get_available_models(api_key)
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

def create_super_prompt(resume_text, style_name):
    # O SEGREDO DO "NANO BANANA": Prompt Engineering Agressivo
    prompt = f"""
    ROLE: You are a World-Class Art Director and Data Visualization Expert using Imagen 3/4 Ultra.
    TASK: Convert the resume below into a highly detailed, text-rich IMAGE GENERATION PROMPT.
    
    TARGET STYLE: {style_name}
    
    INSTRUCTIONS FOR THE PROMPT YOU WILL WRITE:
    1.  The output must be a single, long, descriptive prompt for an image generator.
    2.  Demand a "Text-Rich Infographic Layout".
    3.  Explicitly ask to render the Candidate's Name as the Main Title.
    4.  Ask for a "Chronological Path" or "Timeline" visual structure.
    5.  Specify visual icons for skills (e.g., cloud for AWS, gears for DevOps).
    6.  Force the chosen style ({style_name}) in terms of lighting, texture, and palette.
    7.  Demand "High fidelity text rendering", "Legible fonts", "Professional chart design".
    8.  Do NOT just summarize the career. DESCRIBE THE IMAGE that represents the career.
    
    RESUME DATA:
    {resume_text[:8000]}
    
    OUTPUT: A raw prompt text to be fed into the image generator. Start with: "A high-resolution, text-rich infographic poster in {style_name} style..."
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

def generate_image(prompt_visual, aspect_ratio, model_name):
    ar_param = "1:1"
    if "16:9" in aspect_ratio: ar_param = "16:9"
    elif "9:16" in aspect_ratio: ar_param = "9:16"

    try:
        response = client.models.generate_images(
            model=model_name,
            prompt=prompt_visual,
            config={'aspect_ratio': ar_param}
        )
        return response.generated_images[0].image
    except Exception as e:
        st.error(f"Erro no Modelo {model_name}: {e}")
        return None

# --- INTERFACE PRINCIPAL ---
st.title("HELIOS // RESUME INFOGRAPHIC GEN")

# --- INSTRUÇÕES ---
st.markdown("""
<div class="instruction-box">
    <strong>📘 MANUAL DE OPERAÇÃO:</strong>
    <ul>
        <li><strong>Resultado Esperado:</strong> Um infográfico visual de alta densidade resumindo a carreira.</li>
        <li><strong>Motor Recomendado:</strong> Use o modelo <code>imagen-4.0-ultra</code> para melhor qualidade de texto.</li>
        <li><strong>Processo:</strong> Suba o arquivo -> Configure Estilo -> Clique em GERAR.</li>
        <li><strong>Nota:</strong> O sistema usa Inteligência Artificial Generativa; textos pequenos podem conter "alucinações" visuais (glitches).</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

col1, col2 = st.columns([1, 1])

# Chave de Reset para limpar inputs
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. UPLOAD DO CURRÍCULO")
    uploaded_file = st.file_uploader("ARQUIVO", type=["pdf", "docx", "txt"], key=f"up_{reset_k}")

    st.subheader(">> 2. CONFIGURAÇÃO VISUAL")
    estilo_selecionado = st.selectbox("ESTILO VISUAL", list(ESTILOS.keys()), key=f"st_{reset_k}")
    formato_selecionado = st.selectbox("FORMATO", ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories)"], key=f"fmt_{reset_k}")
    
    st.subheader(">> 3. SELEÇÃO DO MOTOR")
    if available_imagen_models and "ERRO" not in available_imagen_models[0]:
        # Tenta selecionar o Ultra automaticamente se existir
        idx_ultra = 0
        for i, nome in enumerate(available_imagen_models):
            if "ultra" in nome:
                idx_ultra = i
                break
        
        modelo_selecionado = st.selectbox(
            "MODELOS DISPONÍVEIS:", 
            available_imagen_models,
            index=idx_ultra,
            key=f"mod_{reset_k}"
        )
    else:
        modelo_selecionado = st.text_input("Digite o modelo:", "imagen-3.0-generate-001", key=f"mod_txt_{reset_k}")

with col2:
    st.subheader(">> 4. RENDERIZAÇÃO")
    image_placeholder = st.empty()
    
    # Se já temos uma imagem na memória (sessão), mostramos ela direto sem gerar de novo
    if st.session_state.last_image_bytes:
        image = Image.open(io.BytesIO(st.session_state.last_image_bytes))
        image_placeholder.image(image, caption=f"INFOGRÁFICO ({st.session_state.last_model_used})", use_container_width=True)
        
        # Botão de Download (Não vai resetar a vista porque a imagem está na session_state)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        st.download_button("⬇️ BAIXAR (PNG)", data=buf.getvalue(), file_name="helios_resume.png", mime="image/png")
        
        # Botão para gerar por cima (apenas ignora o cache e roda a lógica abaixo)
        st.info("Para gerar uma nova versão com os mesmos ajustes, clique em GERAR novamente.")

    # Botão de Geração
    pode_gerar = uploaded_file is not None and estilo_selecionado and formato_selecionado and modelo_selecionado
    
    if st.button("GERAR INFOGRÁFICO [RENDER]", type="primary", disabled=not pode_gerar, key=f"btn_{reset_k}"):
        if uploaded_file:
            with st.spinner(">> 1/3 LENDO DOCUMENTO..."):
                texto_cv = extract_text_from_file(uploaded_file)
            
            if texto_cv:
                with st.spinner(">> 2/3 PROMPT ENGINEERING (MODO DIREÇÃO DE ARTE)..."):
                    # Aqui está a mágica: Gemini cria o prompt detalhado para o Imagen
                    prompt_otimizado = create_super_prompt(texto_cv, estilo_selecionado)
                
                if prompt_otimizado:
                    with st.spinner(f">> 3/3 RENDERIZANDO COM {modelo_selecionado}..."):
                        # Adiciona a descrição do estilo ao prompt otimizado para garantir fidelidade
                        prompt_final = f"{prompt_otimizado} Style Details: {ESTILOS[estilo_selecionado]}"
                        
                        img_bytes = generate_image(
                            prompt_final, 
                            formato_selecionado,
                            modelo_selecionado
                        )
                        
                        if img_bytes:
                            # SALVA NO ESTADO
                            st.session_state.last_image_bytes = img_bytes.image_bytes
                            st.session_state.last_model_used = modelo_selecionado
                            st.rerun() # Recarrega a página para exibir a imagem do estado
