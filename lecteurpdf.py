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

# --- CONFIGURATION DES MOTEURS IA ---
def setup_engines():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if api_key:
        # Configuration globale de LlamaIndex (RAG)
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

def create_pptx(data, style_name="Professionnel"):
    prs = Presentation()
    bg_color = RGBColor(30, 60, 114) if style_name == "Professionnel" else RGBColor(245, 245, 245)
    
    for slide_data in data.get("slides", []):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg_color
        
        # Titre
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        tf = tb.text_frame
        tf.text = slide_data.get("titre", "Slide")
        
        # Contenu (Points)
        content_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        cf = content_box.text_frame
        for pt in slide_data.get("points", []):
            p = cf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(18)
            p.font.color.rgb = RGBColor(255, 255, 255) if style_name == "Professionnel" else RGBColor(0, 0, 0)
            
    ppt_io = BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF Pro</h1>', unsafe_allow_html=True)
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")
    
    if uploaded_file:
        if 'index' not in st.session_state:
            with st.spinner("Indexation intelligente (RAG) en cours..."):
                pages, full_text = extract_pdf_data(uploaded_file)
                st.session_state.pdf_pages = pages
                st.session_state.full_text = full_text
                
                # Création de l'index vectoriel LlamaIndex
                doc = Document(text=full_text)
                st.session_state.index = VectorStoreIndex.from_documents([doc])
            st.success("Document prêt pour l'analyse !")

# --- AFFICHAGE DES ONGLETS SI LE DOCUMENT EST CHARGÉ ---
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
                # Utilisation de LlamaIndex pour chercher l'info
                query_engine = st.session_state.index.as_query_engine(similarity_top_k=3)
                
                secure_prompt = (
                    f"Réponds UNIQUEMENT en utilisant les informations du document fourni. "
                    f"Si l'information n'est pas présente dans le document, réponds exactement : "
                    f"'Désolé, mais cette information n'est pas présente dans le document.' "
                    f"Question : {prompt}"
                )
                
                response = query_engine.query(secure_prompt)
                st.markdown(response.response)
                st.session_state.messages.append({"role": "assistant", "content": response.response})

    # TAB 2 : SYNTHÈSE
    with tabs[1]:
        s_mode = st.select_slider("Précision du résumé", options=["Court", "Moyen", "Détaillé"])
        if st.button("Lancer la rédaction"):
            with st.spinner("Synthèse en cours..."):
                qe = st.session_state.index.as_query_engine()
                res = qe.query(f"Fais un résumé {s_mode} et bien structuré de ce document.")
                st.info(res.response)

    # TAB 3 : ANALYSE LEXICALE
    with tabs[2]:
        col1, col2 = st.columns(2)
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        freq = Counter([w for w in words if len(w) > 3])
        
        with col1:
            st.metric("Nombre de mots", len(words))
            st.subheader("Mots-clés les plus fréquents")
            for w, c in freq.most_common(10):
                st.write(f"- **{w}** : {c} occurrences")
        
        with col2:
            if st.button("Lancer l'analyse sémantique"):
                qe = st.session_state.index.as_query_engine()
                ana = qe.query("Analyse les thèmes principaux, les concepts clés et le ton général du document.")
                st.write(ana.response)

    # TAB 4 : AUDIO (Lecture de page)
    with tabs[3]:
        page_num = st.number_input("Page à transformer en audio", 1, len(st.session_state.pdf_pages), 1)
        if st.button("Générer la voix"):
            with st.spinner("Lecture de la page..."):
                text_to_read = st.session_state.pdf_pages[page_num]
                tts = gTTS(text=text_to_read, lang='fr')
                audio_io = BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io)

    # TAB 5 : PRÉSENTATION (Corrigé pour éviter l'erreur JSON)
    with tabs[4]:
        n_slides = st.number_input("Nombre de diapositives souhaitées", 3, 10, 5)
        if st.button("Générer le PowerPoint"):
            with st.spinner("L'IA structure vos slides..."):
                try:
                    # Utilisation d'un moteur de requête optimisé pour le JSON
                    qe = st.session_state.index.as_query_engine(response_mode="compact")
                    
                    prompt_ppt = (
                        f"Crée une structure pour une présentation de {n_slides} slides. "
                        f"Réponds UNIQUEMENT avec un objet JSON valide au format exact suivant : "
                        f"{{\"slides\": [{{\"titre\": \"...\", \"points\": [\"...\", \"...\"]}}]}}. "
                        f"Ne mets aucun texte avant ou après le JSON."
                    )
                    
                    raw_res = str(qe.query(prompt_ppt).response)
                    
                    # Nettoyage robuste pour extraire uniquement le bloc JSON
                    start = raw_res.find('{')
                    end = raw_res.rfind('}') + 1
                    
                    if start != -1 and end > 0:
                        clean_json = raw_res[start:end]
                        data_ppt = json.loads(clean_json)
                        
                        ppt_bytes = create_pptx(data_ppt)
                        st.download_button("📥 Télécharger la présentation", ppt_bytes, "presentation_insight.pptx")
                        st.success("La présentation est prête !")
                    else:
                        st.error("L'IA n'a pas pu formater les données. Essayez de réduire le nombre de slides.")
                
                except Exception as e:
                    st.error(f"Une erreur est survenue lors de la génération : {str(e)}")

else:
    st.info("Veuillez charger un fichier PDF dans la barre latérale pour commencer l'exploration.")
