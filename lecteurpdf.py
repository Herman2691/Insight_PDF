import streamlit as st
from mistralai.client import MistralClient
import PyPDF2
from io import BytesIO
import json
import re
from collections import Counter
from datetime import datetime
import os
from gtts import gTTS
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# --- IMPORTS LLAMA-INDEX ---
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.llms.mistralai import MistralAI
from llama_index.embeddings.mistralai import MistralAIEmbedding

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    html, body, [class*="ViewContainer"] { font-family: 'Google Sans', sans-serif; }
    .gemini-gradient {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 700; margin-bottom: 0px;
    }
    .stButton>button { border-radius: 20px; background-color: #f0f4f9; border: none; color: #1a73e8; font-weight: 500; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e1e3e1; }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURATION MOTEURS ---
def setup_engines():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if api_key:
        # Configuration LlamaIndex pour le RAG
        Settings.llm = MistralAI(model="mistral-large-latest", api_key=api_key, temperature=0)
        Settings.embed_model = MistralAIEmbedding(model_name="mistral-embed", api_key=api_key)
        return MistralClient(api_key=api_key)
    return None

mistral_client = setup_engines()

# --- FONCTIONS UTILITAIRES ---
def extract_pdf_data(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    pages_text = {i + 1: p.extract_text() for i, p in enumerate(reader.pages) if p.extract_text()}
    full_text = "\n".join(pages_text.values())
    return pages_text, full_text

def create_pptx(data, style_name):
    prs = Presentation()
    bg_color = RGBColor(30, 60, 114) if style_name == "Professionnel" else RGBColor(245, 245, 245)
    for slide_data in data.get("slides", []):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg_color
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        tb.text_frame.text = slide_data.get("titre", "Slide")
        content = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        for pt in slide_data.get("points", []):
            p = content.text_frame.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(18)
    ppt_io = BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()

# --- INTERFACE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF Pro</h1>', unsafe_allow_html=True)
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")
    if uploaded_file:
        if 'index' not in st.session_state:
            with st.spinner("Indexation intelligente (RAG)..."):
                pages, full_text = extract_pdf_data(uploaded_file)
                st.session_state.pdf_pages = pages
                st.session_state.full_text = full_text
                # Création de l'index vectoriel
                doc = Document(text=full_text)
                st.session_state.index = VectorStoreIndex.from_documents([doc])
            st.success("Analyse terminée !")

if 'index' in st.session_state:
    tabs = st.tabs(["💬 Chat", "📝 Synthèse", "📊 Analyse", "🔊 Audio", "🎯 Présentation"])

    # TAB 1 : CHAT (RAG Stricte)
    with tabs[0]:
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Une question sur le document ?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="✨"):
                query_engine = st.session_state.index.as_query_engine(similarity_top_k=3)
                # On force l'IA à dire "Je ne sais pas" si hors contexte
                instr = f"Réponds UNIQUEMENT via le doc fourni. Si absent, dis que tu ne sais pas. Question: {prompt}"
                response = query_engine.query(instr)
                st.markdown(response.response)
                st.session_state.messages.append({"role": "assistant", "content": response.response})

    # TAB 2 : SYNTHÈSE
    with tabs[1]:
        s_mode = st.select_slider("Précision", options=["Court", "Moyen", "Détaillé"])
        if st.button("Rédiger le résumé"):
            qe = st.session_state.index.as_query_engine()
            res = qe.query(f"Fais un résumé {s_mode} et structuré de ce document.")
            st.info(res.response)

    # TAB 3 : ANALYSE
    with tabs[2]:
        col1, col2 = st.columns(2)
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        freq = Counter([w for w in words if len(w) > 3])
        with col1:
            st.metric("Mots totaux", len(words))
            st.subheader("Mots-clés fréquents")
            for w, c in freq.most_common(10): st.write(f"- **{w}** : {c}")
        with col2:
            if st.button("Analyse sémantique"):
                qe = st.session_state.index.as_query_engine()
                st.write(qe.query("Quels sont les thèmes principaux et le ton ?").response)

    # TAB 4 : AUDIO
    with tabs[3]:
        page_num = st.number_input("Page à lire", 1, len(st.session_state.pdf_pages), 1)
        if st.button("Générer l'audio"):
            with st.spinner("Génération de la voix..."):
                tts = gTTS(text=st.session_state.pdf_pages[page_num], lang='fr')
                audio_io = BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io)

    # TAB 5 : PRÉSENTATION (CORRIGÉ JSON)
    with tabs[4]:
        n_slides = st.number_input("Nombre de slides", 3, 10, 5)
        if st.button("Générer PPTX"):
            with st.spinner("L'IA structure vos slides..."):
                qe = st.session_state.index.as_query_engine()
                prompt_ppt = (
                    f"Crée une structure pour {n_slides} slides. "
                    f"Réponds UNIQUEMENT avec un objet JSON valide : "
                    f"{{\"slides\": [{{\"titre\": \"...\", \"points\": [\"...\", \"...\"]}}]}}"
                )
                raw_response = qe.query(prompt_ppt).response
                
                try:
                    # Extraction sécurisée du JSON
                    clean_json = re.search(r'\{.*\}', str(raw_response), re.DOTALL).group()
                    data_ppt = json.loads(clean_json)
                    ppt_bytes = create_pptx(data_ppt, "Professionnel")
                    st.download_button("📥 Télécharger la présentation", ppt_bytes, "presentation_ia.pptx")
                    st.success("Prêt au téléchargement !")
                except Exception as e:
                    st.error("Erreur de structure. Réessayez, l'IA a été trop bavarde.")
else:
    st.info("Veuillez charger un PDF pour commencer.")
