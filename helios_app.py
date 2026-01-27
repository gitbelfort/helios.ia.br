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
st.set_page_config(page_title="HELIOS | SYSTEM", page_icon="🟡", layout="wide")

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
    
    /* Área de Descrição da Análise */
    .analysis-box {
        border: 1px solid #333;
        background-color: #111;
        padding: 15px;
        margin-top: 10px;
        border-left: 5px solid #00FF00; /* Verde Matrix */
        font-size: 0.9em;
        color: #EEE !important;
    }
    .analysis-title {
        color: #00FF00 !important;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
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

# --- GERENCIAMENTO DE ESTADO ---
if 'last_image_bytes' not in st.session_state:
    st.session_state.last_image_bytes = None
if 'last_token_usage' not in st.session_state:
    st.session_state.last_token_usage = None
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = 0

# Estado para a Análise Prévia
if 'analyzed_content' not in st.session_state:
    st.session_state.analyzed_content = None # Texto descritivo para o usuário
if 'ready_prompt' not in st.session_state:
    st.session_state.ready_prompt = None # Prompt técnico para o Nano Banana
if 'last_uploaded_file_id' not in st.session_state:
    st.session_state.last_uploaded_file_id = None

def reset_all():
    st.session_state.last_image_bytes = None
    st.session_state.last_token_usage = None
    st.session_state.analyzed_content = None
    st.session_state.ready_prompt = None
    st.session_state.last_uploaded_file_id = None
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
    st.markdown("**UNIVERSAL INFOGRAPHIC**")
    api_key = st.text_input("CHAVE DE ACESSO (API KEY)", type="password")
    st.markdown("---")
    if st.button("♻️ LIMPAR TUDO"):
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
    Processa arquivos e retorna o objeto Part correto.
    CORREÇÃO APLICADA: mime_type passado como keyword argument.
    """
    try:
        # IMAGEM
        if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
            # CORREÇÃO: mime_type=...
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

def analyze_and_create_prompt(content_part, style_name, idioma, densidade):
    """
    Função Dupla:
    1. Gera uma Descrição para o Usuário (Resumo).
    2. Gera o Prompt Técnico para o Nano Banana.
    """
    
    instrucao_densidade = ""
    if densidade == "Conciso":
        instrucao_densidade = "Use MINIMAL TEXT. Focus heavily on icons/headlines."
    elif densidade == "Detalhado (BETA)":
        instrucao_densidade = "Use HIGH TEXT DENSITY. Include detailed descriptions."
    else:
        instrucao_densidade = "Use BALANCED TEXT and VISUALS."

    prompt_text = f"""
    ROLE: Elite Content Analyst & Art Director.
    TASK: Analyze the Input (Text/Image) and output TWO distinct sections.
    
    SECTION 1: USER_SUMMARY
    - Write a short paragraph (in Portuguese) describing exactly what was identified in the file.
    - Example: "Identifiquei uma foto de um prato de Feijoada com arroz, couve e laranja." or "Identifiquei o currículo de um Engenheiro de Software Sênior."
    
    SECTION 2: PROMPT
    - Write a highly detailed IMAGE GENERATION PROMPT for Gemini/Nano Banana based on the analysis.
    - LOGIC:
      - Resume -> Career Timeline.
      - Food -> Recipe & Variations.
      - Object -> Tech Specs & History.
      - Place -> Travel Guide.
    - CONFIG: Style={style_name}, Language={idioma}, Density={instrucao_densidade}.
    - CRITICAL: "Render all visible text in {idioma}".
    
    OUTPUT FORMAT:
    USER_SUMMARY: [Your summary here]
    PROMPT: [Your long prompt here]
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
        
        # Parser simples para separar o Resumo do Prompt
        summary = "Análise concluída."
        prompt = ""
        
        if "USER_SUMMARY:" in result_text and "PROMPT:" in result_text:
            parts = result_text.split("PROMPT:")
            summary_part = parts[0].replace("USER_SUMMARY:", "").strip()
            prompt_part = parts[1].strip()
            return summary_part, prompt_part, response.usage_metadata
        else:
            # Fallback se a IA não formatar direito
            return "Conteúdo identificado. Pronto para gerar.", result_text, response.usage_metadata
        
    except Exception as e:
        st.error(f"Erro na análise inteligente: {e}")
        return None, None, None

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
            u = token_info
            info_text = f"Input: {u.prompt_token_count} | Output: {u.candidates_token_count}"
            st.markdown(f"<div class='token-box'>💎 CUSTO DE ANÁLISE:<br>{info_text}</div>", unsafe_allow_html=True)

# --- UI ---
st.title("HELIOS // UNIVERSAL INFOGRAPHIC")

col1, col2 = st.columns([1, 1])
reset_k = st.session_state.reset_trigger

with col1:
    st.subheader(">> 1. INPUT UNIVERSAL")
    uploaded_file = st.file_uploader(
        "ARQUIVO (DOCS OU IMAGENS)", 
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"], 
        key=f"up_{reset_k}"
    )

    # --- LÓGICA DE ANÁLISE IMEDIATA ---
    if uploaded_file:
        # Verifica se é um arquivo novo para não re-analisar a cada clique
        current_file_id = uploaded_file.file_id if hasattr(uploaded_file, 'file_id') else uploaded_file.name
        
        if current_file_id != st.session_state.last_uploaded_file_id:
            # É um arquivo novo! Limpa resultados anteriores e analisa
            st.session_state.analyzed_content = None
            st.session_state.ready_prompt = None
            st.session_state.last_image_bytes = None # Limpa imagem antiga
            
            with st.spinner("🧠 CÉREBRO GEMINI: Lendo e Entendendo o arquivo..."):
                # Captura parâmetros atuais do form para o primeiro prompt
                # (O usuário pode mudar depois e re-analisar se quiser, mas pegamos o default)
                # Nota: Para ser perfeito, teríamos que re-analisar se o usuário mudar o estilo.
                # Mas para "descrever o conteúdo", o estilo não importa tanto.
                # Vamos usar um default para a análise inicial.
                
                content_part = process_uploaded_file(uploaded_file)
                if content_part:
                    # Analisa com os defaults atuais da UI (mesmo que ainda não renderizados)
                    # Como estamos no mesmo script run, usamos defaults seguros
                    summary, prompt, tokens = analyze_and_create_prompt(
                        content_part, 
                        "HYPERBOLD TYPOGRAPHY", # Default para análise
                        "Português (Brasil)", 
                        "Padrão"
                    )
                    
                    st.session_state.analyzed_content = summary
                    st.session_state.ready_prompt = prompt # Prompt base
                    st.session_state.last_token_usage = tokens
                    st.session_state.last_uploaded_file_id = current_file_id

        # Exibe a análise SE ela existir
        if st.session_state.analyzed_content:
            st.markdown(f"""
            <div class="analysis-box">
                <div class="analysis-title">✅ CONTEÚDO IDENTIFICADO:</div>
                {st.session_state.analyzed_content}
            </div>
            """, unsafe_allow_html=True)


    st.subheader(">> 2. CONFIGURAÇÃO")
    # Nota: Se o usuário mudar o estilo aqui, precisaremos atualizar o prompt na hora de gerar
    # pois o prompt "guardado" na análise inicial usou o estilo default.
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
        preview_placeholder.image(img_preview, caption="PREVIEW", width=400)
        
        if st.button("🔍 AMPLIAR / DOWNLOAD", type="secondary", key=f"modal_btn_{reset_k}"):
            show_full_image(st.session_state.last_image_bytes, st.session_state.last_token_usage)

    # Habilita botão se tiver análise feita
    pode_gerar = st.session_state.analyzed_content is not None
    
    label_btn = "GERAR INFOGRÁFICO [RENDER]"
    if st.session_state.last_image_bytes:
        label_btn = "♻️ RE-GERAR (SUBSTITUIR ATUAL)"
    
    if st.button(label_btn, type="primary", disabled=not pode_gerar, key=f"btn_gen_{reset_k}"):
        # RE-ANALISE RÁPIDA PARA APLICAR ESTILO/IDIOMA NOVO
        # Como o usuário pode ter mudado o estilo APÓS o upload,
        # precisamos atualizar o prompt antes de gerar a imagem.
        
        with st.spinner(">> ATUALIZANDO ROTEIRO E RENDERIZANDO..."):
            content_part = process_uploaded_file(uploaded_file)
            
            # Recria o prompt com as configurações finais escolhidas
            _, prompt_final_tecnico, _ = analyze_and_create_prompt(
                content_part, 
                estilo_selecionado, 
                idioma_selecionado, 
                densidade_selecionada
            )
            
            # Adiciona detalhes do estilo
            prompt_completo = f"{prompt_final_tecnico} Style Details: {ESTILOS[estilo_selecionado]}"
            
            img_bytes_raw = generate_image(prompt_completo, formato_selecionado)
            
            if img_bytes_raw:
                st.session_state.last_image_bytes = img_bytes_raw
                st.rerun()
