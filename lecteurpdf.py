import streamlit as st
import os
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import PyPDF2
from mistralai import Mistral
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

# ─── LOGIQUE RAG ────────────────────────────────────────────────────────────
def process_pdf(pdf_file, api_key):
    try:
        reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        if not text.strip():
            return None, "PDF vide ou image seule."
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_text(text)
        db_name = f"db_{int(datetime.now().timestamp())}"
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(chunks, embeddings, collection_name=db_name)
        return vectorstore, text
    except Exception as e:
        return None, str(e)

# ─── SESSION STATE ───────────────────────────────────────────────────────────
defaults = {
    "vs": None,
    "txt": "",
    "chat_history": [],
    "page": "assistant",   # navigation manuelle : "assistant" | "stats"
    "ready": False,        # flag : PDF analysé ?
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── CLEF API ────────────────────────────────────────────────────────────────
api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛠️ Configuration")

    if not api_key:
        st.error("⚠️ MISTRAL_API_KEY manquante dans les secrets Streamlit.")

    uploaded_file = st.file_uploader("Charger un document PDF", type=["pdf"])

    if uploaded_file and st.button("Lancer l'analyse ✨", use_container_width=True):
        if not client:
            st.error("Clé API non configurée.")
        else:
            with st.spinner("Analyse sémantique..."):
                vs, result = process_pdf(uploaded_file, api_key)
            if vs:
                st.session_state.vs = vs
                st.session_state.txt = result
                st.session_state.chat_history = []
                st.session_state.ready = True
                st.session_state.page = "assistant"
                st.success("✅ Analyse terminée !")
                # PAS de st.rerun() — on laisse Streamlit re-rendre seul
            else:
                st.error(result)

    if st.session_state.ready:
        st.divider()
        # Navigation : radio bouton simple = stable, pas de st.tabs()
        page = st.radio(
            "Vue",
            ["💬 Assistant", "📊 Statistiques"],
            index=0 if st.session_state.page == "assistant" else 1,
            label_visibility="collapsed",
        )
        st.session_state.page = "assistant" if page == "💬 Assistant" else "stats"

        if st.button("🗑️ Effacer tout", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()   # seul rerun autorisé : reset complet, état propre

# ─── PAGE PRINCIPALE ─────────────────────────────────────────────────────────
st.title("✨ Insight PDF Pro")

if not st.session_state.ready:
    st.info("👈 Importez un PDF dans le menu latéral pour commencer.")
    st.stop()

# ── VUE ASSISTANT ─────────────────────────────────────────────────────────────
if st.session_state.page == "assistant":

    # Affichage de l'historique — rendu statique, aucun widget interactif dedans
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input séparé, hors de tout contexte conditionnel
    prompt = st.chat_input("Posez votre question sur le document...")

    if prompt:
        if not client:
            st.error("Clé API non configurée.")
            st.stop()

        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Réflexion..."):
                try:
                    docs = st.session_state.vs.similarity_search(prompt, k=4)
                    context = "\n\n".join([d.page_content for d in docs])

                    # Historique glissant (3 derniers échanges) inclus dans le prompt
                    history = st.session_state.chat_history[-6:]
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "Tu es un assistant expert. "
                                "Réponds uniquement à partir du contexte fourni, "
                                "en français.\n\nCONTEXTE:\n" + context
                            ),
                        },
                        *[{"role": m["role"], "content": m["content"]} for m in history],
                    ]

                    response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=messages,
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": answer}
                    )
                except Exception as e:
                    st.error(f"Erreur lors de la génération : {e}")

# ── VUE STATISTIQUES ──────────────────────────────────────────────────────────
elif st.session_state.page == "stats":

    words = len(st.session_state.txt.split())
    chars = len(st.session_state.txt)
    reading_time = max(1, words // 200)

    # st.metric() — composant natif, zéro HTML injecté
    col1, col2, col3 = st.columns(3)
    col1.metric("Mots", f"{words:,}")
    col2.metric("Temps de lecture", f"{reading_time} min")
    col3.metric("Caractères", f"{chars:,}")

    st.divider()
    st.subheader("Aperçu du texte extrait")
    preview = st.session_state.txt[:2000]
    if len(st.session_state.txt) > 2000:
        preview += "\n\n[...]"
    st.text_area("", preview, height=300, disabled=True)

# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.caption(f"© {datetime.now().year} Insight PDF Pro — Kandolo Herman")
