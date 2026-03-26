"""
Insight PDF - Analyseur de Documents Intelligent (Version Pro - RAG)
Développé par Kandolo Herman - Chercheur en IA
"""

import streamlit as st
import os
import re
import json
from io import BytesIO
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

# --- CORRECTIF POUR CHROMADB SUR STREAMLIT CLOUD ---
# ChromaDB nécessite une version récente de pysqlite3
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import PyPDF2
from mistralai import Mistral

# Imports LangChain (Version 0.1+)
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Charger les variables d'environnement
load_dotenv()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Insight PDF - AI Document Analysis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Inter:wght@300;400;500;600&display=swap');
    * { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #f8f9fa; }
    .header-gradient {
        background: linear-gradient(135deg, #0b57d0 0%, #1e3c72 100%);
        padding: 2.5rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 10px 30px rgba(11, 87, 208, 0.2);
    }
    .stat-card {
        background: white; padding: 20px; border-radius: 15px;
        border: 1px solid #e3e3e3; text-align: center;
    }
    .stat-val { font-size: 2rem; font-weight: 700; color: #0b57d0; }
    .audit-box { padding: 15px; border-radius: 12px; margin-bottom: 10px; color: white !important; }
    .audit-tone { background-color: #1a73e8; }
    .audit-clarity { background-color: #34a853; }
    .audit-errors { background-color: #d93025; }
    .audit-suggestions { background-color: #f9ab00; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE RAG & IA ---

def process_pdf_to_rag(pdf_file, api_key):
    """Découpe le PDF et crée une base de connaissance temporaire."""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"
        
        # Découpage en morceaux (Chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(full_text)
        
        # Création des embeddings et du VectorStore (en mémoire)
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(texts=chunks, embedding=embeddings)
        
        return vectorstore, full_text
    except Exception as e:
        st.error(f"Erreur RAG : {str(e)}")
        return None, ""

def query_with_context(client, vectorstore, question):
    """Recherche les passages pertinents et interroge Mistral."""
    try:
        # Recherche des 3 morceaux les plus pertinents
        docs = vectorstore.similarity_search(question, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        messages = [
            {"role": "system", "content": "Tu es un expert en analyse de documents. Utilise le contexte fourni pour répondre."},
            {"role": "user", "content": f"CONTEXTE :\n{context}\n\nQUESTION : {question}"}
        ]
        response = client.chat.complete(model="mistral-large-latest", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur lors de la génération : {str(e)}"

# --- INITIALISATION ---

if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'full_text' not in st.session_state:
    st.session_state.full_text = ""

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- UI ---

with st.sidebar:
    st.title("⚙️ Paramètres")
    if not api_key:
        st.warning("Clé API manquante")
    
    uploaded_file = st.file_uploader("Charger un PDF", type=['pdf'])
    if uploaded_file and st.button("Indexer le document"):
        with st.spinner("Création de la base de connaissance..."):
            vs, txt = process_pdf_to_rag(uploaded_file, api_key)
            st.session_state.vectorstore = vs
            st.session_state.full_text = txt
            st.success("Indexation terminée !")

st.markdown("""
    <div class="header-gradient">
        <h1>🧠 Insight PDF Pro (RAG Edition)</h1>
        <p>Analyse sémantique profonde via Mistral AI</p>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.vectorstore:
    st.info("Veuillez charger et indexer un document dans la barre latérale.")
    st.stop()

# --- ONGLETS ---
t1, t2, t3 = st.tabs(["💬 Assistant", "📝 Synthèse", "📊 Stats"])

with t1:
    q = st.text_input("Posez une question sur le document :")
    if q:
        with st.spinner("Recherche dans le document..."):
            ans = query_with_context(client, st.session_state.vectorstore, q)
            st.markdown(ans)

with t3:
    words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
    c1, c2 = st.columns(2)
    c1.metric("Nombre de mots", len(words))
    c2.metric("Vocabulaire unique", len(Counter(words)))

# Pied de page
st.markdown("<br><hr><center>Insight PDF Pro • Kandolo Herman</center>", unsafe_allow_html=True)
