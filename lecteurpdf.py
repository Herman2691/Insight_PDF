import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

# --- CORRECTIF POUR CHROMADB SUR STREAMLIT CLOUD ---
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

# Charger les variables d'environnement
load_dotenv()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Insight PDF - Gemini Style",
    page_icon="✨",
    layout="wide",
)

# --- DESIGN STYLE GEMINI (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="ViewContainer"] {
        font-family: 'Google Sans', sans-serif;
        background-color: #ffffff !important;
    }

    /* Gradient Animation for Title */
    .gemini-gradient {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570, #4285f4);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradient 5s linear infinite;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0px;
    }

    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f0f4f9 !important;
        border-right: None;
    }

    /* Stat Cards */
    .stat-card {
        background: #f8fafd;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #e1e3e1;
        text-align: left;
    }

    /* Custom Chat Input Container */
    .stChatInput {
        border-radius: 32px !important;
        border: 1px solid #dfe1e5 !important;
        padding: 10px !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 20px;
        padding: 0px 20px;
        background-color: #f0f4f9;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background-color: #c2e7ff !important;
        color: #001d35 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE RAG (Inchangée mais optimisée) ---

def process_pdf_to_rag(pdf_file, api_key):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        full_text = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content: full_text += content + "\n"
        
        if not full_text.strip():
            return None, "Le PDF est vide ou scanné sans OCR."
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_text(full_text)
        
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(
            texts=chunks, 
            embedding=embeddings,
            collection_name=f"pdf_{datetime.now().timestamp()}"
        )
        return vectorstore, full_text
    except Exception as e:
        return None, str(e)

def query_with_context(client, vectorstore, question):
    try:
        docs = vectorstore.similarity_search(question, k=4)
        context = "\n\n".join([doc.page_content for doc in docs])
        messages = [
            {"role": "system", "content": "Tu es un expert en analyse de documents. Réponds de façon structurée et fluide."},
            {"role": "user", "content": f"CONTEXTE :\n{context}\n\nQUESTION : {question}"}
        ]
        response = client.chat.complete(model="mistral-large-latest", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur : {str(e)}"

# --- SESSION STATE ---
if 'vectorstore' not in st.session_state: st.session_state.vectorstore = None
if 'full_text' not in st.session_state: st.session_state.full_text = ""
if 'pdf_indexed' not in st.session_state: st.session_state.pdf_indexed = False

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- SIDEBAR GEMINI STYLE ---
with st.sidebar:
    st.markdown("<h2 style='color:#1a73e8;'>Menu</h2>", unsafe_allow_html=True)
    if not api_key:
        st.warning("⚠️ Clé API Mistral requise.")
    
    uploaded_file = st.file_uploader("Importer un document", type=['pdf'])
    
    if uploaded_file:
        if st.button("✨ Analyser le document", use_container_width=True):
            with st.status("Lecture sémantique...", expanded=True) as status:
                vs, res = process_pdf_to_rag(uploaded_file, api_key)
                if vs:
                    st.session_state.vectorstore = vs
                    st.session_state.full_text = res
                    st.session_state.pdf_indexed = True
                    status.update(label="Analyse terminée !", state="complete", expanded=False)
                else:
                    st.error(res)

    if st.session_state.pdf_indexed:
        st.divider()
        if st.button("Nouveau document", type="secondary", use_container_width=True):
            st.session_state.vectorstore = None
            st.session_state.pdf_indexed = False
            st.rerun()

# --- INTERFACE PRINCIPALE ---
st.markdown('<p class="gemini-gradient">Insight PDF Pro</p>', unsafe_allow_html=True)
st.markdown("<p style='color:#5f6368; font-size:1.1rem; margin-top:-10px;'>Propulsé par l'IA de Kandolo Herman</p>", unsafe_allow_html=True)

if not st.session_state.pdf_indexed:
    st.container()
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("""
        ### Bonjour. 
        Comment puis-je vous aider avec votre document aujourd'hui ?
        
        * **Synthèse instantanée** : Résumez de longs rapports en secondes.
        * **Recherche sémantique** : Trouvez des informations cachées.
        * **Analyse de données** : Extrayez les chiffres clés.
        """)
    st.info("Veuillez charger un fichier PDF dans la barre latérale pour activer l'assistant.")
    st.stop()

# --- TABS ---
tab1, tab2 = st.tabs(["💬 Assistant", "📊 Données"])

with tab1:
    # Zone de Chat
    chat_container = st.container()
    user_query = st.chat_input("Demandez n'importe quoi sur le document...")
    
    if user_query:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)
        
        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("Réflexion..."):
                answer = query_with_context(client, st.session_state.vectorstore, user_query)
                st.markdown(answer)

with tab2:
    if st.session_state.full_text:
        words = re.findall(r'\b\w+\b', st.session_state.full_text.lower())
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'<div class="stat-card"><small>Volume</small><br><b>{len(words)} Mots</b></div>', unsafe_allow_html=True)
        with col2:
            unique = len(Counter(words))
            st.markdown(f'<div class="stat-card"><small>Complexité</small><br><b>{unique} Termes uniques</b></div>', unsafe_allow_html=True)
        with col3:
            reading_time = max(1, len(words) // 200)
            st.markdown(f'<div class="stat-card"><small>Lecture estimée</small><br><b>{reading_time} min</b></div>', unsafe_allow_html=True)
        
        st.markdown("### Aperçu du contenu")
        st.info("Le contenu ci-dessous a été indexé dans la base vectorielle.")
        st.text_area("", st.session_state.full_text[:2000] + "...", height=250)

# Footer
st.markdown(f"""
    <div style="text-align:center; padding-top:50px; color:#bdc1c6; font-size:0.85rem;">
        Insight PDF Pro ✨ {datetime.now().year} • Technologie RAG
    </div>
""", unsafe_allow_html=True)
