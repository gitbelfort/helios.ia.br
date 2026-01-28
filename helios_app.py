import streamlit as st
import os
import datetime
from google import genai
from google.genai import types
from PIL import Image
import io
import pypdf
import docx

# --- ÁREA DE SEGURANÇA (HARDCODE OPCIONAL) ---
CHAVE_MESTRA = None 

# --- CONFIGURAÇÃO VISUAL TRON (RESPONSIVO) ---
st.set_page_config(
    page_title="HELIOS | SYSTEM", 
    page_icon="🟡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    .stApp { background-color: #000000; color: #FFD700; font-family: 'Share Tech Mono', monospace; }
    
    /* Esconde Sidebar para Fullscreen */
    [data-testid="stSidebar"] { display: none; }
    
    h1, h2, h3, p, label, span, div, li { color: #FFD700 !important; font-family: 'Share Tech Mono', monospace !important; }
    
    .stTextInput, .stSelectbox, .stFileUploader, .stRadio { color: #FFD700; }
    .stSelectbox > div > div { background-color: #111; color: #FFD700; border: 1px solid #FFD700; }
    
    /* Botões */
    .stButton > button { 
        background-color: #000000; color: #FFD700; border: 2px solid #FFD700; 
        border-radius: 0px; text-transform: uppercase; transition: 0.3s; width: 100%; font-weight: bold; font-size: 1.1em;
    }
    .stButton > button:hover { background-color: #FFD700; color: #000000; box-shadow: 0 0 20px #FFD700; }
    
    /* Upload */
    [data-testid='stFileUploader'] { border: 1px dashed #FFD700; padding: 20px; background-color: #050505; }
    
    /* Caixas de Texto */
    .analysis-box {
        border: 1px solid #333;
        background-color: #111;
        padding: 15px;
        margin-top: 10px;
        border-left: 5px solid #00FF00;
        font-size: 0.9em;
        color: #EEE !important;
    }
    .analysis-title { color: #00FF00 !important; font-weight: bold; margin-bottom: 5px; }
    
    .instruction-box {
        border: 1px solid #FFD700;
        background-color: #0a0a0a;
        padding: 15px;
        margin-bottom: 25px;
        border-left: 8px solid #FFD700;
    }
    
    .token-box {
        font-size: 0.8em;
        color: #888 !important;
        margin-top: 10px;
        border-top: 1px solid #333;
        padding-top: 5px;
    }
    
    /* Radio Buttons Custom */
    div[role="radiogroup"] > label > div:first-child {
        background-color: #111;
        border-color: #FFD700;
    }

    /* Footer */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #000000; color: #00FF00 !important;
        text-align: center; padding: 10px; font-size: 0.9em;
        border-top: 1px solid #222; z-index: 999;
        font-family: 'Share Tech Mono', monospace; letter-spacing: 2px;
    }
    
    div[data-testid="stDialog"] { background-color: #000000; border: 2px solid #FFD700; }
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- MODELO ---
MODELO_IMAGEM_FIXO = "gemini-3-pro-image-preview"

# --- ESTADO ---
keys_to_init = [
    'last_image_bytes', 'last_token_usage', 'reset_trigger', 
    'analyzed_content', 'file_type_detected', 'last_uploaded_file_id'
]
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'reset_trigger' else 0

def reset_all():
    st.session_state.last_image_bytes = None
    st.session_state.last_token_usage = None
    st.session_state.analyzed_content = None
    st.session_state.file_type_detected = None
    st.session_state.last_uploaded_file_id = None
    st.session_state.reset_trigger += 1

# --- ESTILOS ---
ESTILOS = {
    "ANIME BATTLE AESTHETIC": "High-Octane Anime Battle aesthetic. Intense action frames, dramatic energy effects, sharp angles. Colors: electric blues, fiery reds.",
    "3D NEUMORPHISM AESTHETIC": "Tactile 3D Neumorphism. Ultra-soft UI elements, extruded shapes, realistic soft shadows, matte silicone finishes. Clean minimalist palette.",
    "90s/Y2K PIXEL AESTHETIC": "90s/Y2K Retro Video Game aesthetic. 16-bit pixel art, bright neon/bubblegum colors, chunky typography, CRT scanline effects.",
    "WHITEBOARD ANIMATION": "Classic Whiteboard Animation. Hand-drawn dry-erase marker sketches on white background. Educational and direct.",
    "MINI WORLD (DIORAMA)": "Isometric Miniature Diorama. Playful voxel art, macro photography feel, tilt-shift effect, vibrant 'toy-like' textures.",
    "PHOTO REALIST": "Ultra-realistic 8k cinematic photography. Sophisticated interior/studio lighting, sharp details, realistic textures, deep depth of field.",
    "RETRO-FUTURISM": "Nostalgic Retro Futurism. 90s sci-fi warmth, neon lighting (teals/purples), chrome surfaces, film grain/VHS texture.",
    "HYPERBOLD TYPOGRAPHY": "Hyperbold High-Contrast. Massive heavy typography, brutalist shapes. Strict Black & White with one neon accent. Urgent and impactful."
}

# --- AUTH ---
api_key = None
if CHAVE_MESTRA:
    api_key = CHAVE_MESTRA
elif "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

if not api_key:
    st.title("🟡 HELIOS SYSTEM")
    st.markdown("### 🔐 ACESSO RESTRITO REQUERIDO")
    api_key = st.text_input("INSIRA A CHAVE DE ACESSO (API KEY)", type="password")
    if not api_key: st.stop()

client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

# --- FUNÇÕES ---

def process_uploaded_file(uploaded_file):
    """Lê arquivos com limites de segurança (30 págs ou 100k chars)"""
    try:
        # IMAGEM
        if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            return types.Part(inline_data=types.Blob(mime_type=uploaded_file.type, data=uploaded_file.getvalue())), "IMAGE"
        
        # TEXTO
        text_content = ""
        page_count = 0
        
        if uploaded_file.type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            page_count = len(reader.pages)
            if page_count > 30:
                return "LIMIT_ERROR", "PDF excede 30 páginas."
            for page in reader.pages: text_content += page.extract_text() + "\n"
            
        elif "wordprocessingml" in uploaded_file.type:
            doc = docx.Document(uploaded_file)
            # Estimativa simples para DOCX (não tem páginas reais sem renderizar)
            text_content = "\n".join([p.text for p in doc.paragraphs])
            
        else: # txt
            text_content = uploaded_file.read().decode("utf-8")
        
        # Limite Geral de Caracteres (aprox. 30 paginas densas)
        if len(text_content) > 100000:
            return "LIMIT_ERROR", "Texto excede o limite de processamento (aprox. 30 pgs)."
            
        return types.Part.from_text(text=text_content), "TEXT"
        
    except Exception as e:
        st.error(f"Erro de leitura: {e}")
        return None, None

def initial_analysis(content_part, file_type):
    """Análise rápida apenas para identificar o conteúdo e mostrar resumo ao usuário"""
    prompt = """
    ROLE: Elite Content Analyst.
    TASK: Identify the input content concisely in Portuguese.
    OUTPUT: A single short paragraph starting with 'Identifiquei...'.
    Examples: 'Identifiquei um currículo de Engenheiro...', 'Identifiquei uma foto de um prato de Sushi...', 'Identifiquei um relatório financeiro...'.
    """
    try:
        if file_type == "TEXT":
            contents = [types.Part.from_text(text=prompt), content_part]
        else: # IMAGE
            contents = [types.Part.from_text(text=prompt), content_part]
            
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=contents
        )
        return response.text
    except Exception as e:
        return f"Conteúdo carregado. (Erro na análise prévia: {e})"

def create_final_prompt(content_part, file_type, mode, style_name, idioma, densidade):
    """Gera o prompt final complexo baseado na escolha do usuário"""
    
    instrucao_densidade = ""
    if densidade == "Conciso": instrucao_densidade = "Use MINIMAL TEXT. Focus on visual impact."
    elif densidade == "Detalhado (BETA)": instrucao_densidade = "Use HIGH TEXT DENSITY. Detailed descriptions."
    else: instrucao_densidade = "Use BALANCED TEXT and VISUALS."

    # Lógica Condicional Poderosa
    logic_instruction = ""
    
    if file_type == "IMAGE":
        if mode == "APLICAR ESTILO VISUAL (RE-IMAGINE)":
            logic_instruction = f"""
            TASK: VISUAL STYLE TRANSFER / RE-IMAGINATION.
            1. Analyze the input image scene, composition, and objects precisely.
            2. Write a prompt to RECREATE this exact scene but strictly in the {style_name} style.
            3. Do NOT add new informational text or infographics unless they exist in the original image.
            4. Focus on lighting, texture, and artistic fidelity to {style_name}.
            """
        else: # MODO EXPLICATIVO
            logic_instruction = f"""
            TASK: EDUCATIONAL INFOGRAPHIC GENERATION.
            1. Identify the main subject of the image (Object, Food, Person, Place).
            2. Retrieve external knowledge about it:
               - IF FOOD: Provide the RECIPE, Ingredients, and ORIGIN/HISTORY.
               - IF OBJECT/GADGET: Provide Technical Specs, History, and Utility.
               - IF LIVING BEING: Provide Biology, Habitat, or Fun Facts.
            3. Create a layout where the subject is central, surrounded by this retrieved data.
            4. Style: {style_name}.
            """
            
    else: # TEXT
        logic_instruction = f"""
        TASK: TEXT TO INFOGRAPHIC CONVERSION.
        1. Analyze the text document.
        2. IF RESUME/CV: Create a 'Career Timeline' infographic highlighting roles and skills.
        3. IF GENERAL TEXT: Create a 'Visual Summary' or 'Mind Map' infographic. Extract key takeaways, data points, and concepts.
        4. Organize the information logically in {style_name} style.
        """

    full_prompt = f"""
    ROLE: World-Class Art Director & Data Viz Expert.
    {logic_instruction}
    
    GLOBAL CONFIG:
    - Target Language for Text inside Image: {idioma}
    - Density: {instrucao_densidade}
    - Critical: Render text legibly.
    
    OUTPUT: Write ONLY the raw image generation prompt for the AI model. Start with 'A high-resolution...'
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[types.Part.from_text(text=full_prompt), content_part]
        )
        return response.text, response.usage_metadata
    except Exception as e:
        st.error(f"Erro no cérebro: {e}")
        return None, None

def generate_image_pixels(prompt_text, aspect_ratio):
    ar = "1:1"
    if "16:9" in aspect_ratio: ar = "16:9"
    elif "9:16" in aspect_ratio: ar = "9:16"
    try:
        response = client.models.generate_content(
            model=MODELO_IMAGEM_FIXO,
            contents=[types.Part.from_text(text=prompt_text)],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio=ar))
        )
        for part in response.parts:
            if part.inline_data: return part.inline_data.data
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
    filename = f"helios-v5-{ts}.png"
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ BAIXAR ARQUIVO", data=image_bytes, file_name=filename, mime="image/png", type="primary", use_container_width=True)
    with c2:
        if token_info:
            u = token_info
            st.markdown(f"<div class='token-box'>💎 CUSTO INTELIGÊNCIA:<br>In: {u.prompt_token_count} | Out: {u.candidates_token_count}</div>", unsafe_allow_html=True)

# --- UI PRINCIPAL ---
st.title("🟡 HELIOS // UNIVERSAL v5.1")

st.markdown(f"""
<div class="instruction-box">
    <strong>📘 MANUAL DE OPERAÇÕES v5.1:</strong>
    <ul>
        <li><strong>1. Input Universal:</strong> Suba seu arquivo de texto (PDF/DOC/TXT) ou imagem (JPG/PNG). O sistema entende o que é.</li>
        <li><strong>2. Modo de Imagem:</strong> Se subir uma foto, escolha entre <em>"Apenas Estilizar"</em> (Visual) ou <em>"Explicativo"</em> (Receitas/Dados).</li>
        <li><strong>3. Modo de Texto:</strong> Currículos viram Timelines; Textos comuns viram Resumos Visuais.</li>
        <li><strong>4. Limites:</strong> Documentos até 30 páginas para performance máxima.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. INPUT UNIVERSAL")
    uploaded_file = st.file_uploader("ARQUIVO (DOCS OU IMAGENS)", type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"], key=f"up_{reset_k}")

    # Lógica de Análise Imediata
    if uploaded_file:
        current_id = uploaded_file.file_id if hasattr(uploaded_file, 'file_id') else uploaded_file.name
        if current_id != st.session_state.last_uploaded_file_id:
            # Novo arquivo detectado -> Analisar
            st.session_state.analyzed_content = None
            st.session_state.file_type_detected = None
            st.session_state.last_image_bytes = None
            
            with st.spinner("🧠 CÉREBRO GEMINI: VERIFICANDO CONTEÚDO..."):
                content_part, ftype = process_uploaded_file(uploaded_file)
                
                if content_part == "LIMIT_ERROR":
                    st.error(f"⛔ {ftype}")
                elif content_part:
                    summary = initial_analysis(content_part, ftype)
                    st.session_state.analyzed_content = summary
                    st.session_state.file_type_detected = ftype
                    st.session_state.last_uploaded_file_id = current_id

        # Exibe Resultado da Análise
        if st.session_state.analyzed_content:
            st.markdown(f"""<div class="analysis-box"><div class="analysis-title">✅ CONTEÚDO VERIFICADO:</div>{st.session_state.analyzed_content}</div>""", unsafe_allow_html=True)

    # Configurações
    st.subheader(">> 2. CONFIGURAÇÃO")
    
    # OPÇÃO EXTRA PARA IMAGENS (SÓ APARECE SE FOR IMAGEM)
    modo_imagem = "PADRÃO"
    if st.session_state.file_type_detected == "IMAGE":
        st.markdown("**O QUE FAZER COM ESTA IMAGEM?**")
        modo_imagem = st.radio(
            "MODO DE OPERAÇÃO",
            ["APLICAR ESTILO VISUAL (RE-IMAGINE)", "CRIAR INFOGRÁFICO EXPLICATIVO (DADOS/RECEITA)"],
            index=1,
            label_visibility="collapsed",
            key=f"mode_{reset_k}"
        )
        if "Explicativo" in modo_imagem:
            st.caption("ℹ️ O sistema irá identificar o objeto/prato e adicionar curiosidades, receitas ou dados técnicos.")
        else:
            st.caption("ℹ️ O sistema manterá a cena original, alterando apenas a estética artística.")
        st.markdown("---")

    estilo = st.selectbox("ESTILO VISUAL", list(ESTILOS.keys()), key=f"st_{reset_k}")
    fmt = st.selectbox("FORMATO", ["1:1 (Quadrado)", "16:9 (Paisagem)", "9:16 (Stories)"], key=f"fmt_{reset_k}")
    
    st.subheader(">> 3. CONTEÚDO")
    lang = st.selectbox("IDIOMA", ["Português (Brasil)", "Inglês", "Espanhol", "Francês"], key=f"lang_{reset_k}")
    dens = st.selectbox("DENSIDADE", ["Conciso", "Padrão", "Detalhado (BETA)"], index=1, key=f"dens_{reset_k}")

    # BOTÕES LADO A LADO
    st.markdown("---")
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        if st.button("LIMPAR TELA", use_container_width=True, key=f"clr_{reset_k}"):
            reset_all()
            st.rerun()
    with b_col2:
        # Habilita geração apenas se houver arquivo válido
        pode_gerar = st.session_state.file_type_detected is not None
        if st.button("GERAR IMAGEM", type="primary", use_container_width=True, disabled=not pode_gerar, key=f"gen_{reset_k}"):
            
            # GERAÇÃO (Processo Completo)
            with st.spinner(">> CRIANDO ROTEIRO E RENDERIZANDO PIXELS..."):
                # Recarrega arquivo (necessário para stream)
                uploaded_file.seek(0)
                c_part, f_type = process_uploaded_file(uploaded_file)
                
                if c_part and c_part != "LIMIT_ERROR":
                    # 1. Cria Prompt Técnico
                    final_prompt, tokens = create_final_prompt(
                        c_part, f_type, modo_imagem, estilo, lang, dens
                    )
                    
                    if final_prompt:
                        # 2. Renderiza Imagem
                        # Adiciona detalhes do estilo ao prompt para garantir fidelidade
                        prompt_w_style = f"{final_prompt} Style Guidelines: {ESTILOS[estilo]}"
                        img_bytes = generate_image_pixels(prompt_w_style, fmt)
                        
                        if img_bytes:
                            st.session_state.last_image_bytes = img_bytes
                            st.session_state.last_token_usage = tokens
                            st.rerun()

with col2:
    st.subheader(">> 4. RESULTADO")
    preview_placeholder = st.empty()
    if st.session_state.last_image_bytes:
        img_preview = Image.open(io.BytesIO(st.session_state.last_image_bytes))
        preview_placeholder.image(img_preview, caption="PREVIEW", width=400)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 CLIQUE AQUI PARA AMPLIAR / BAIXAR", type="secondary", use_container_width=True, key=f"zoom_{reset_k}"):
            show_full_image(st.session_state.last_image_bytes, st.session_state.last_token_usage)
    else:
        # Placeholder visual quando vazio
        st.info("Aguardando geração...")

# --- RODAPÉ ---
st.markdown("""
<div class="footer">
    🟢 SISTEMA ONLINE &nbsp;|&nbsp; HELIOS.IA.BR
</div>
""", unsafe_allow_html=True)
