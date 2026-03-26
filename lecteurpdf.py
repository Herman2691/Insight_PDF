"""
Insight PDF - Analyseur de Documents Intelligent (Version Pro - RAG)
Développé par Kandolo Herman - Chercheur en IA
"""

import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

# --- CORRECTIF POUR CHROMADB SUR STREAMLIT CLOUD ---
# Ce bloc est indispensable pour éviter les erreurs de version SQLite sur Streamlit Cloud
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

# Charger les variables d'environnement (Clé API)
load_dotenv()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Insight PDF - AI Document Analysis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN PREMIUM (CSS STABILISÉ) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="ViewContainer"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 { font-family: 'Google Sans', sans-serif !important; }
    
    .stApp { background-color: #f8f9fa; }
    
    .header-gradient {
        background: linear-gradient(135deg, #0b57d0 0%, #1e3c72 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .stat-card {
        background: white; 
        padding: 20px; 
        border-radius: 15px;
        border: 1px solid #e3e3e3; 
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE RAG & IA ---

def process_pdf_to_rag(pdf_file, api_key):
    """Extrait le texte, le découpe en segments et crée l'index vectoriel."""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        full_text = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                full_text += content + "\n"
        
        if not full_text.strip():
            return None, "Le PDF semble vide ou contient uniquement des images (OCR requis)."
            
        # Découpage en morceaux (Chunks) pour respecter la fenêtre de contexte
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_text(full_text)
        
        # Création des embeddings et stockage en mémoire via ChromaDB
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(
            texts=chunks, 
            embedding=embeddings,
            collection_name=f"pdf_analysis_{datetime.now().timestamp()}"
        )
        
        return vectorstore, full_text
    except Exception as e:
        return None, str(e)

def query_with_context(client, vectorstore, question):
    """Récupère les segments pertinents et génère une réponse avec Mistral."""
    try:
        # Recherche de similarité (Top 4 segments)
        docs = vectorstore.similarity_search(question, k=4)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        messages = [
            {"role": "system", "content": "Tu es un expert en analyse de documents. Utilise exclusivement le contexte fourni pour répondre de manière concise et précise."},
            {"role": "user", "content": f"CONTEXTE :\n{context}\n\nQUESTION : {question}"}
        ]
        response = client.chat.complete(model="mistral-large-latest", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Désolé, une erreur est survenue lors de l'analyse : {str(e)}"

# --- GESTION DE L'ÉTAT (SESSION STATE) ---

if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'full_text' not in st.session_state:
    st.session_state.full_text = ""
if 'pdf_indexed' not in st.session_state:
    st.session_state.pdf_indexed = False

# Récupération de la clé API
api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- BARRE LATÉRALE ---

with st.sidebar:
    st.markdown("### ⚙️ Panneau de Contrôle")
    if not api_key:
        st.error("🔑 Clé API Mistral manquante dans les secrets/env.")
    
    uploaded_file = st.file_uploader("1. Charger un document PDF", type=['pdf'])
    
    if uploaded_file:
        if st.button("2. Lancer l'Indexation", use_container_width=True, type="primary"):
            with st.spinner("Analyse sémantique..."):
                vs, res = process_pdf_to_rag(uploaded_file, api_key)
                if vs:
                    st.session_state.vectorstore = vs
                    st.session_state.full_text = res
                    st.session_state.pdf_indexed = True
                    st.success("✅ Indexation terminée !")
                else:
                    st.error(f"Erreur : {res}")

    if st.session_state.pdf_indexed:
        st.divider()
        if st.button("Réinitialiser l'analyse", type="secondary", use_container_width=True):
            st.session_state.vectorstore = None
            st.session_state.full_text = ""
            st.session_state.pdf_indexed = False
            st.rerun()

# --- INTERFACE PRINCIPALE ---

st.markdown("""
    <div class="header-gradient">
        <h1 style="margin:0;">🧠 Insight PDF Pro</h1>
        <p style="margin:0; opacity:0.8;">Intelligence Artificielle & Recherche Sémantique (RAG)</p>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.pdf_indexed:
    st.info("👋 Bienvenue ! Veuillez charger et indexer un PDF dans le menu latéral pour commencer.")
    st.stop()

# --- NAVIGATION PAR ONGLETS ---
tab1, tab2 = st.tabs(["💬 Assistant Intelligent", "📊 Analyse Statistique"])

with tab1:
    st.subheader("Interroger le document")
    # Utilisation de st.chat_input pour une meilleure stabilité du DOM (évite l'erreur removeChild)
    user_query = st.chat_input("Posez votre question ici...")
    
    if user_query:
        with st.chat_message("user"):
            st.write(user_query)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyse des segments pertinents..."):
                answer = query_with_context(client, st.session_state.vectorstore, user_query)
                st.markdown(answer)

with tab2:
    if st.session_state.full_text:
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'<div class="stat-card"><h3>Mots</h3><p style="font-size:2rem; color:#0b57d0;">{len(words)}</p></div>', unsafe_allow_html=True)
        with col2:
            unique = len(Counter(words))
            st.markdown(f'<div class="stat-card"><h3>Vocabulaire</h3><p style="font-size:2rem; color:#0b57d0;">{unique}</p></div>', unsafe_allow_html=True)
        with col3:
            reading_time = max(1, len(words) // 200)
            st.markdown(f'<div class="stat-card"><h3>Lecture</h3><p style="font-size:2rem; color:#0b57d0;">~{reading_time} min</p></div>', unsafe_allow_html=True)
            
        st.divider()
        st.subheader("Aperçu du texte indexé")
        st.text_area("Extrait du contenu brut", st.session_state.full_text[:3000] + "...", height=300)

# Pied de page
st.markdown(f"""
    <div style="text-align:center; padding-top:40px; color:#5f6368; font-size:0.8rem; border-top:1px solid #eee; margin-top:30px;">
        <b>Insight PDF Pro</b> • Développé par Kandolo Herman • {datetime.now().year}
    </div>
""", unsafe_allow_html=True)
