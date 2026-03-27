import streamlit as st
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
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

# --- CONFIGURATION & STYLE GEMINI ---
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
    .stButton>button:hover { background-color: #e1e3e1; border: 1px solid #4285f4; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e1e3e1; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE TECHNIQUE MISTRAL ---
def get_mistral_client():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    return MistralClient(api_key=api_key)

def query_mistral(prompt, context=""):
    try:
        client = get_mistral_client()
        messages = [
            ChatMessage(role="system", content="Tu es un assistant expert en analyse de documents."),
            ChatMessage(role="user", content=f"CONTEXTE:\n{context}\n\nINSTRUCTION: {prompt}")
        ]
        response = client.chat(model="mistral-large-latest", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur API : {str(e)}"

# --- FONCTIONS UTILITAIRES ---
def extract_pdf_text(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    return {i + 1: p.extract_text() for i, p in enumerate(reader.pages) if p.extract_text()}

def create_pptx(data, style_name):
    prs = Presentation()
    # Logique simplifiée de création (Professionnel par défaut)
    bg_color = RGBColor(30, 60, 114) if style_name == "Professionnel" else RGBColor(245, 245, 245)
    
    for slide_data in data.get("slides", []):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Appliquer fond
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = bg_color
        
        # Titre
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        tf = tb.text_frame
        tf.text = slide_data.get("titre", "Slide")
        
        # Points
        content = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        cf = content.text_frame
        for pt in slide_data.get("points", []):
            p = cf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(18)
    
    ppt_io = BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF</h1>', unsafe_allow_html=True)
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")
    if uploaded_file:
        if 'pdf_text' not in st.session_state:
            with st.spinner("Analyse du document..."):
                st.session_state.pdf_text = extract_pdf_text(uploaded_file)
                st.session_state.full_text = "\n".join(st.session_state.pdf_text.values())
        st.success(f"Document chargé : {len(st.session_state.pdf_text)} pages")

if 'pdf_text' in st.session_state:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📝 Synthèse", "📊 Analyse", "🔊 Audio", "🎯 Présentation"])

    # TAB 1 : CHAT
    with tab1:
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Une question sur le document ?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="✨"):
                response = query_mistral(prompt, st.session_state.full_text[:10000])
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    # TAB 2 : SYNTHÈSE
    with tab2:
        s_mode = st.select_slider("Précision", options=["Court", "Moyen", "Détaillé"])
        if st.button("Rédiger le résumé"):
            res = query_mistral(f"Fais un résumé {s_mode} de ce document.", st.session_state.full_text[:12000])
            st.info(res)

    # TAB 3 : ANALYSE LEXICALE
    with tab3:
        col1, col2 = st.columns(2)
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        freq = Counter([w for w in words if len(w) > 3])
        
        with col1:
            st.metric("Mots totaux", len(words))
            st.subheader("Mots-clés fréquents")
            for w, c in freq.most_common(10):
                st.write(f"- **{w}** : {c} occurrences")
        
        with col2:
            if st.button("Lancer l'analyse sémantique"):
                ana = query_mistral("Analyse les thèmes principaux et le ton du document.", st.session_state.full_text[:8000])
                st.write(ana)

    # TAB 4 : AUDIO
    with tab4:
        page_num = st.number_input("Page à lire", min_value=1, max_value=len(st.session_state.pdf_text), value=1)
        lang_audio = st.selectbox("Langue", [("Français", "fr"), ("English", "en")])
        if st.button("Générer l'audio"):
            text_to_read = st.session_state.pdf_text[page_num]
            tts = gTTS(text=text_to_read, lang=lang_audio[1])
            audio_path = f"temp_page_{page_num}.mp3"
            tts.save(audio_path)
            st.audio(audio_path)

    # TAB 5 : PRÉSENTATION
    with tab5:
        n_slides = st.number_input("Nombre de slides", 3, 15, 5)
        p_style = st.selectbox("Style visuel", ["Professionnel", "Moderne", "Minimaliste"])
        if st.button("Générer le PowerPoint"):
            with st.spinner("L'IA structure vos slides..."):
                prompt_ppt = f"Crée une structure JSON pour {n_slides} slides : {{'slides': [{{'titre': '...', 'points': ['...']}}]}}"
                structure_raw = query_mistral(prompt_ppt, st.session_state.full_text[:10000])
                try:
                    # Nettoyage simple du JSON si Mistral ajoute du texte autour
                    json_str = re.search(r'\{.*\}', structure_raw, re.DOTALL).group()
                    data_ppt = json.loads(json_str)
                    ppt_bytes = create_pptx(data_ppt, p_style)
                    st.download_button("📥 Télécharger la présentation", data=ppt_bytes, file_name="presentation_ia.pptx")
                except:
                    st.error("Erreur lors de la génération de la structure. Réessayez.")

else:
    st.info("Veuillez charger un fichier PDF dans la barre latérale pour commencer l'analyse.")
