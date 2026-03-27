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
from mistralai import Mistral
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIGURATION ---
st.set_page_config(page_title="Insight PDF", page_icon="✨")

# Utilisation des secrets Streamlit pour la sécurité
# Allez dans Settings > Secrets sur Streamlit Cloud pour ajouter MISTRAL_API_KEY
api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")

if not api_key:
    st.error("🔑 Clé API Mistral introuvable. Ajoutez-la dans les Secrets Streamlit.")
    st.stop()

client = Mistral(api_key=api_key)

# --- STYLE GEMINI (Stable) ---
st.markdown("""
    <style>
    .gemini-title {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "vs" not in st.session_state:
    st.session_state.vs = None
    st.session_state.messages = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("📁 Document")
    uploaded_file = st.file_uploader("Charger un PDF", type="pdf")
    if uploaded_file and st.button("Analyser le PDF"):
        with st.spinner("Indexation en cours..."):
            reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
            
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = splitter.split_text(text)
            
            embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
            st.session_state.vs = Chroma.from_texts(chunks, embeddings)
            st.success("Analyse terminée !")

# --- UI PRINCIPALE ---
st.markdown('<p class="gemini-title">Insight PDF Pro</p>', unsafe_allow_html=True)

if st.session_state.vs:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Posez votre question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Réflexion..."):
                docs = st.session_state.vs.similarity_search(prompt, k=3)
                context = "\n".join([d.page_content for d in docs])
                
                resp = client.chat.complete(
                    model="mistral-large-latest",
                    messages=[
                        {"role": "system", "content": "Réponds en te basant sur le contexte."},
                        {"role": "user", "content": f"Contexte: {context}\n\nQuestion: {prompt}"}
                    ]
                )
                ans = resp.choices[0].message.content
                st.write(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
else:
    st.info("👋 Chargez un PDF pour commencer l'analyse intelligente.")
