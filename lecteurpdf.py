import streamlit as st
import os
from io import BytesIO

# --- FIX CHROMADB ---
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import PyPDF2
# --- ANCIENNE SYNTAXE MISTRAL ---
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
# --------------------------------

from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

# --- STYLE INTERFACE GEMINI ---
st.markdown("""
    <style>
    .gemini-title {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800;
        font-family: 'Segoe UI', sans-serif;
        margin-bottom: 0px;
    }
    .stApp { background-color: #ffffff; }
    /* Style pour les messages de chat */
    .stChatMessage { border-radius: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION API ---
api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")

if not api_key:
    st.warning("🔑 Clé API Mistral manquante dans les Secrets Streamlit.")
    st.stop()

# Initialisation du client avec l'ancienne syntaxe
client = MistralClient(api_key=api_key)

if "vs" not in st.session_state:
    st.session_state.vs = None
    st.session_state.history = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("📁 Documents")
    file = st.file_uploader("Importer un PDF", type="pdf")
    if file and st.button("Lancer l'analyse ✨", use_container_width=True):
        with st.spinner("Lecture et indexation..."):
            reader = PyPDF2.PdfReader(BytesIO(file.read()))
            text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
            
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            chunks = splitter.split_text(text)
            
            embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
            st.session_state.vs = Chroma.from_texts(chunks, embeddings)
            st.success("Analyse terminée avec succès !")

# --- MAIN UI ---
st.markdown('<h1 class="gemini-title">Insight PDF</h1>', unsafe_allow_html=True)
st.write("### Analyse intelligente de documents")

if not st.session_state.vs:
    st.info("👋 Bonjour ! Veuillez charger un document PDF dans le menu latéral pour commencer.")
else:
    # Affichage de l'historique
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Zone de saisie
    if prompt := st.chat_input("Posez votre question sur le document..."):
        st.session_state.history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("Réflexion..."):
                # RAG : Recherche de contexte
                docs = st.session_state.vs.similarity_search(prompt, k=3)
                context = "\n\n".join([d.page_content for d in docs])
                
                # --- APPEL MISTRAL CLIENT (Ancienne syntaxe) ---
                messages = [
                    ChatMessage(role="system", content="Tu es un expert. Réponds en utilisant le contexte fourni."),
                    ChatMessage(role="user", content=f"CONTEXTE:\n{context}\n\nQUESTION: {prompt}")
                ]
                
                response = client.chat(
                    model="mistral-large-latest",
                    messages=messages
                )
                
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.history.append({"role": "assistant", "content": answer})
