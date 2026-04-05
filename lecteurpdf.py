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

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.llms.mistralai import MistralAI
from llama_index.embeddings.mistralai import MistralAIEmbedding

# --- CONFIGURATION ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

# FIX: CSS injecté une seule fois via st.html() stable, sans balises dynamiques
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Google Sans', sans-serif; }
.stButton>button {
    border-radius: 20px;
    background-color: #f0f4f9;
    border: none;
    color: #1a73e8;
    font-weight: 500;
}
[data-testid="stSidebar"] {
    background-color: #f8f9fa;
    border-right: 1px solid #e1e3e1;
}
</style>
""", unsafe_allow_html=True)


# --- CONFIGURATION DES MOTEURS IA ---
def setup_engines():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if api_key:
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
    bg_color = RGBColor(30, 60, 114)
    for slide_data in data.get("slides", []):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg_color

        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        tf = tb.text_frame
        tf.text = slide_data.get("titre", "Slide")
        p_titre = tf.paragraphs[0]
        p_titre.font.color.rgb = RGBColor(255, 255, 255)
        p_titre.font.bold = True
        p_titre.font.size = Pt(24)

        content = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        cf = content.text_frame
        cf.word_wrap = True
        for pt in slide_data.get("points", []):
            p = cf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(18)
            p.font.color.rgb = RGBColor(255, 255, 255)

    ppt_io = BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()


# --- INTERFACE ---
# FIX: Titre sans unsafe_allow_html pour éviter le conflit DOM React
st.title("✨ Insight PDF Pro")
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

if not engine_ready:
    st.error("Clé API Mistral manquante dans les secrets.")

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")

    if uploaded_file:
        # FIX: Clé unique basée sur le nom du fichier pour éviter les re-render inutiles
        file_key = uploaded_file.name
        if st.session_state.get("loaded_file") != file_key:
            with st.spinner("Indexation intelligente (RAG)..."):
                pages, full_text = extract_pdf_data(uploaded_file)
                st.session_state.pdf_pages = pages
                st.session_state.full_text = full_text
                st.session_state.messages = []
                doc = Document(text=full_text)
                st.session_state.index = VectorStoreIndex.from_documents([doc])
                st.session_state.loaded_file = file_key
            st.success("Analyse terminée !")
        else:
            st.info(f"📄 {file_key} déjà chargé.")


# --- ONGLETS PRINCIPAUX ---
if "index" in st.session_state:
    tabs = st.tabs(["💬 Chat", "📝 Synthèse", "📊 Analyse", "🔊 Audio", "🎯 Présentation"])

    # TAB 1 : CHAT
    with tabs[0]:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # FIX: Affichage des messages sans unsafe_allow_html
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("Posez une question sur le document..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant", avatar="✨"):
                with st.spinner("Recherche en cours..."):
                    qe = st.session_state.index.as_query_engine(similarity_top_k=3)
                    res = qe.query(
                        f"Réponds en te basant uniquement sur le document. "
                        f"Si la réponse n'est pas dans le document, dis-le clairement. "
                        f"Question: {prompt}"
                    )
                    st.write(res.response)
                    st.session_state.messages.append({"role": "assistant", "content": res.response})

    # TAB 2 : SYNTHÈSE
    with tabs[1]:
        s_mode = st.select_slider(
            "Niveau de précision",
            options=["Court", "Moyen", "Détaillé"],
            value="Moyen"
        )
        if st.button("📝 Rédiger le résumé", key="btn_resume"):
            with st.spinner("Génération du résumé..."):
                qe = st.session_state.index.as_query_engine()
                res = qe.query(f"Fais un résumé {s_mode} et structuré de ce document.")
                st.info(res.response)

    # TAB 3 : ANALYSE
    with tabs[2]:
        col1, col2 = st.columns(2)
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        stop_words = {"les", "des", "une", "que", "qui", "dans", "pour", "avec", "sur", "par", "est", "sont"}
        freq = Counter([w for w in words if len(w) > 3 and w not in stop_words])

        with col1:
            st.metric("Mots totaux", len(words))
            st.metric("Pages analysées", len(st.session_state.pdf_pages))
            st.subheader("🔑 Mots-clés fréquents")
            for w, c in freq.most_common(10):
                st.write(f"- **{w}** : {c} occurrences")

        with col2:
            if st.button("🔍 Analyse sémantique", key="btn_semantic"):
                with st.spinner("Analyse en cours..."):
                    qe = st.session_state.index.as_query_engine()
                    result = qe.query("Quels sont les thèmes principaux de ce document ? Liste-les clairement.")
                    st.write(result.response)

    # TAB 4 : AUDIO
    with tabs[3]:
        max_page = len(st.session_state.pdf_pages)
        p_num = st.number_input("Numéro de page à lire", min_value=1, max_value=max_page, value=1)
        lang = st.selectbox("Langue", ["fr", "en", "es"], index=0)

        if st.button("🔊 Générer l'audio", key="btn_audio"):
            page_text = st.session_state.pdf_pages.get(p_num, "")
            if page_text:
                with st.spinner("Génération audio..."):
                    tts = gTTS(text=page_text, lang=lang)
                    audio_io = BytesIO()
                    tts.write_to_fp(audio_io)
                    audio_io.seek(0)
                    st.audio(audio_io, format="audio/mp3")
            else:
                st.warning("Aucun texte trouvé sur cette page.")

    # TAB 5 : PRÉSENTATION
    with tabs[4]:
        n_slides = st.number_input("Nombre de slides", min_value=3, max_value=10, value=5)

        if st.button("🎯 Générer la présentation PPTX", key="btn_pptx"):
            with st.spinner("L'IA structure vos slides..."):
                try:
                    qe = st.session_state.index.as_query_engine(response_mode="compact")
                    p_ppt = (
                        f"Crée une structure pour exactement {n_slides} slides basées sur ce document. "
                        f"Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après : "
                        f'{{ "slides": [ {{ "titre": "...", "points": ["...", "...", "..."] }} ] }}'
                    )
                    raw = str(qe.query(p_ppt).response)
                    start = raw.find('{')
                    end = raw.rfind('}') + 1
                    if start != -1 and end > 0:
                        data = json.loads(raw[start:end])
                        ppt_bytes = create_pptx(data)
                        st.download_button(
                            label="📥 Télécharger la présentation",
                            data=ppt_bytes,
                            file_name="presentation.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        )
                        st.success(f"✅ Présentation avec {len(data.get('slides', []))} slides prête !")
                    else:
                        st.error("Format JSON invalide reçu de l'IA.")
                except json.JSONDecodeError as e:
                    st.error(f"Erreur de parsing JSON : {e}")
                except Exception as e:
                    st.error(f"Erreur inattendue : {e}")

else:
    st.info("👈 Veuillez charger un fichier PDF dans la barre latérale pour commencer.")
