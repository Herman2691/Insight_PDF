import streamlit as st
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
from pptx.dml.color import RGBColor

# --- IMPORTS LLAMA-INDEX (Ils gèrent Mistral en interne) ---
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

# --- CONFIGURATION DES MOTEURS IA ---
def setup_engines():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if api_key:
        # On configure LlamaIndex pour utiliser Mistral pour le texte ET les embeddings
        Settings.llm = MistralAI(model="mistral-large-latest", api_key=api_key, temperature=0)
        Settings.embed_model = MistralAIEmbedding(model_name="mistral-embed", api_key=api_key)
        return True
    return False

engine_ready = setup_engines()

# --- FONCTIONS UTILITAIRES ---
def extract_pdf_data(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    pages_text = {i + 1: p.extract_text() for i, p in enumerate(reader.pages) if p.extract_text()}
    full_text = "\n".join(pages_text.values())
    return pages_text, full_text

def create_pptx(data):
    prs = Presentation()
    # Style Pro (Bleu sombre)
    bg_color = RGBColor(30, 60, 114) 
    for slide_data in data.get("slides", []):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg_color
        
        # Titre en blanc
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        tf = tb.text_frame
        tf.text = slide_data.get("titre", "Slide")
        p_titre = tf.paragraphs[0]
        p_titre.font.color.rgb = RGBColor(255, 255, 255)
        p_titre.font.bold = True
        
        # Points en blanc
        content = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        cf = content.text_frame
        for pt in slide_data.get("points", []):
            p = cf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(18)
            p.font.color.rgb = RGBColor(255, 255, 255)
            
    ppt_io = BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()

# --- INTERFACE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF Pro</h1>', unsafe_allow_html=True)
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

if not engine_ready:
    st.error("Clé API Mistral manquante dans les secrets.")

with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")
    if uploaded_file:
        if 'index' not in st.session_state:
            with st.spinner("Indexation intelligente (RAG)..."):
                pages, full_text = extract_pdf_data(uploaded_file)
                st.session_state.pdf_pages = pages
                st.session_state.full_text = full_text
                # Création de l'index
                doc = Document(text=full_text)
                st.session_state.index = VectorStoreIndex.from_documents([doc])
            st.success("Analyse terminée !")

if 'index' in st.session_state:
    tabs = st.tabs(["💬 Chat", "📝 Synthèse", "📊 Analyse", "🔊 Audio", "🎯 Présentation"])

    # TAB 1 : CHAT
    with tabs[0]:
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Posez une question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant", avatar="✨"):
                qe = st.session_state.index.as_query_engine(similarity_top_k=3)
                res = qe.query(f"Réponds via le doc. Sinon dis que tu ne sais pas. Question: {prompt}")
                st.markdown(res.response)
                st.session_state.messages.append({"role": "assistant", "content": res.response})

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
            st.subheader("Mots-clés")
            for w, c in freq.most_common(10): st.write(f"- **{w}** : {c}")
        with col2:
            if st.button("Analyse sémantique"):
                qe = st.session_state.index.as_query_engine()
                st.write(qe.query("Quels sont les thèmes principaux ?").response)

    # TAB 4 : AUDIO
    with tabs[3]:
        p_num = st.number_input("Page à lire", 1, len(st.session_state.pdf_pages), 1)
        if st.button("Générer l'audio"):
            tts = gTTS(text=st.session_state.pdf_pages[p_num], lang='fr')
            audio_io = BytesIO()
            tts.write_to_fp(audio_io)
            st.audio(audio_io)

    # TAB 5 : PRÉSENTATION
    with tabs[4]:
        n_slides = st.number_input("Nombre de slides", 3, 10, 5)
        if st.button("Générer PPTX"):
            with st.spinner("L'IA structure vos slides..."):
                try:
                    qe = st.session_state.index.as_query_engine(response_mode="compact")
                    p_ppt = (
                        f"Crée une structure pour {n_slides} slides. "
                        f"Réponds UNIQUEMENT avec un JSON valide : "
                        f"{{\"slides\": [{{\"titre\": \"...\", \"points\": [\"...\", \"...\"]}}]}}"
                    )
                    raw = str(qe.query(p_ppt).response)
                    start, end = raw.find('{'), raw.rfind('}') + 1
                    if start != -1 and end > 0:
                        data = json.loads(raw[start:end])
                        ppt = create_pptx(data)
                        st.download_button("📥 Télécharger", ppt, "presentation.pptx")
                        st.success("Prêt !")
                    else: st.error("Échec du formatage JSON.")
                except Exception as e: st.error(f"Erreur : {e}")
else:
    st.info("Veuillez charger un PDF.")
