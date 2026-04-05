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
from mistralai import Mistral

# --- CONFIGURATION ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

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


# --- CLIENT MISTRAL DIRECT (sans llama-index) ---
def get_client():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None
    return Mistral(api_key=api_key)

def ask_mistral(client, context: str, question: str) -> str:
    try:
        max_chars = 25000
        ctx = context[:max_chars] if len(context) > max_chars else context
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant expert en analyse de documents. "
                        "Réponds uniquement en te basant sur le document fourni. "
                        "Si la réponse n'est pas dans le document, dis-le clairement. "
                        "Réponds toujours en français sauf si demandé autrement."
                    )
                },
                {
                    "role": "user",
                    "content": f"DOCUMENT:\n{ctx}\n\nQUESTION: {question}"
                }
            ],
            temperature=0,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur Mistral : {e}"


# --- FONCTIONS UTILITAIRES ---
def extract_pdf_data(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    pages_text = {}
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages_text[i + 1] = text
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
        p = tf.paragraphs[0]
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.font.bold = True
        p.font.size = Pt(24)

        content = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        cf = content.text_frame
        cf.word_wrap = True
        for pt in slide_data.get("points", []):
            para = cf.add_paragraph()
            para.text = f"• {pt}"
            para.font.size = Pt(18)
            para.font.color.rgb = RGBColor(255, 255, 255)

    ppt_io = BytesIO()
    prs.save(ppt_io)
    return ppt_io.getvalue()


# --- INTERFACE ---
st.title("✨ Insight PDF Pro")
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

client = get_client()
if not client:
    st.error("⚠️ Clé API Mistral manquante. Ajoutez MISTRAL_API_KEY dans les secrets Streamlit.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")

    if uploaded_file:
        file_key = uploaded_file.name
        if st.session_state.get("loaded_file") != file_key:
            with st.spinner("Extraction du texte..."):
                pages, full_text = extract_pdf_data(uploaded_file)
                if not full_text.strip():
                    st.error("Le PDF semble vide ou non lisible (PDF scanné ?).")
                    st.stop()
                st.session_state.pdf_pages = pages
                st.session_state.full_text = full_text
                st.session_state.messages = []
                st.session_state.loaded_file = file_key
            st.success(f"✅ {len(pages)} pages chargées !")
        else:
            st.info(f"📄 {file_key} déjà chargé.")

    if "pdf_pages" in st.session_state:
        st.divider()
        st.metric("Pages", len(st.session_state.pdf_pages))
        st.metric("Caractères", f"{len(st.session_state.full_text):,}")


# --- ONGLETS PRINCIPAUX ---
if "pdf_pages" in st.session_state:
    tabs = st.tabs(["💬 Chat", "📝 Synthèse", "📊 Analyse", "🔊 Audio", "🎯 Présentation"])

    # TAB 1 : CHAT
    with tabs[0]:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("Posez une question sur le document..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant", avatar="✨"):
                with st.spinner("Analyse en cours..."):
                    response = ask_mistral(client, st.session_state.full_text, prompt)
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

    # TAB 2 : SYNTHÈSE
    with tabs[1]:
        s_mode = st.select_slider(
            "Niveau de précision",
            options=["Court", "Moyen", "Détaillé"],
            value="Moyen"
        )
        longueur = {"Court": "en 5 phrases", "Moyen": "en 10-15 phrases", "Détaillé": "de manière exhaustive"}

        if st.button("📝 Rédiger le résumé", key="btn_resume"):
            with st.spinner("Génération du résumé..."):
                question = f"Fais un résumé structuré {longueur[s_mode]} de ce document, avec des sections claires."
                result = ask_mistral(client, st.session_state.full_text, question)
                st.info(result)

    # TAB 3 : ANALYSE
    with tabs[2]:
        col1, col2 = st.columns(2)
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        stop_words = {
            "les", "des", "une", "que", "qui", "dans", "pour", "avec", "sur",
            "par", "est", "sont", "this", "that", "from", "have", "been",
            "will", "leur", "leurs", "mais", "donc", "comme", "plus", "aussi"
        }
        freq = Counter([w for w in words if len(w) > 3 and w not in stop_words])

        with col1:
            st.metric("Mots totaux", f"{len(words):,}")
            st.metric("Pages analysées", len(st.session_state.pdf_pages))
            st.subheader("🔑 Mots-clés fréquents")
            for w, c in freq.most_common(10):
                st.write(f"- **{w}** : {c} occurrences")

        with col2:
            if st.button("🔍 Analyse sémantique", key="btn_semantic"):
                with st.spinner("Analyse en cours..."):
                    result = ask_mistral(
                        client,
                        st.session_state.full_text,
                        "Quels sont les thèmes principaux de ce document ? Liste-les et explique chacun brièvement."
                    )
                    st.write(result)

    # TAB 4 : AUDIO
    with tabs[3]:
        max_page = len(st.session_state.pdf_pages)
        p_num = st.number_input("Numéro de page à lire", min_value=1, max_value=max_page, value=1)
        lang = st.selectbox("Langue", ["fr", "en", "es", "de"], index=0)

        if st.button("🔊 Générer l'audio", key="btn_audio"):
            page_text = st.session_state.pdf_pages.get(p_num, "")
            if page_text:
                with st.spinner("Génération audio..."):
                    try:
                        tts = gTTS(text=page_text, lang=lang)
                        audio_io = BytesIO()
                        tts.write_to_fp(audio_io)
                        audio_io.seek(0)
                        st.audio(audio_io, format="audio/mp3")
                    except Exception as e:
                        st.error(f"Erreur audio : {e}")
            else:
                st.warning("Aucun texte trouvé sur cette page.")

    # TAB 5 : PRÉSENTATION
    with tabs[4]:
        n_slides = st.number_input("Nombre de slides", min_value=3, max_value=10, value=5)

        if st.button("🎯 Générer la présentation PPTX", key="btn_pptx"):
            with st.spinner("L'IA structure vos slides..."):
                try:
                    question = (
                        f"Crée une structure pour exactement {n_slides} slides basées sur ce document. "
                        f"Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après, sans balises markdown : "
                        f'{{ "slides": [ {{ "titre": "Titre de la slide", "points": ["Point 1", "Point 2", "Point 3"] }} ] }}'
                    )
                    raw = ask_mistral(client, st.session_state.full_text, question)
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")

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
                        st.success(f"✅ {len(data.get('slides', []))} slides générées !")
                    else:
                        st.error("Format JSON invalide reçu.")
                        st.code(raw)
                except json.JSONDecodeError as e:
                    st.error(f"Erreur JSON : {e}")
                    st.code(raw)
                except Exception as e:
                    st.error(f"Erreur : {e}")

else:
    st.info("👈 Veuillez charger un fichier PDF dans la barre latérale pour commencer.")
