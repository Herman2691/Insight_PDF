import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

# --- FIX CHROMADB (Indispensable pour Streamlit Cloud) ---
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

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

# --- CSS STABLE (Pas d'import de polices externes qui cassent le DOM) ---
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .gemini-title {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 700;
    }
    /* Style minimaliste pour les cartes */
    .stat-card {
        padding: 1.5rem; border-radius: 1rem;
        background-color: #f0f4f9; border: 1px solid #e1e3e1;
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE RAG ---
def process_pdf(pdf_file, api_key):
    try:
        reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        if not text.strip(): return None, "PDF vide ou image seule."
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_text(text)
        
        # Collection unique par session pour éviter les conflits de fichiers
        db_name = f"db_{int(datetime.now().timestamp())}"
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(chunks, embeddings, collection_name=db_name)
        
        return vectorstore, text
    except Exception as e:
        return None, str(e)

# --- GESTION DE L'ÉTAT (SESSION STATE) ---
if 'vs' not in st.session_state: st.session_state.vs = None
if 'txt' not in st.session_state: st.session_state.txt = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🛠️ Configuration")
    file = st.file_uploader("Charger un document PDF", type=['pdf'])
    
    if file and st.button("Lancer l'Analyse ✨", use_container_width=True):
        with st.status("Analyse sémantique...", expanded=False) as status:
            vs, text = process_pdf(file, api_key)
            if vs:
                st.session_state.vs = vs
                st.session_state.txt = text
                status.update(label="Analyse terminée !", state="complete")
                st.rerun() # Rafraîchissement propre
            else:
                st.error(text)

    if st.session_state.vs:
        if st.button("Effacer tout", type="secondary", use_container_width=True):
            st.session_state.vs = None
            st.session_state.chat_history = []
            st.rerun()

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-title">Insight PDF Pro</h1>', unsafe_allow_html=True)

if not st.session_state.vs:
    st.write("### Bonjour. Que souhaitez-vous analyser ?")
    st.info("👈 Commencez par importer un document PDF dans le menu latéral.")
else:
    tab1, tab2 = st.tabs(["💬 Assistant", "📊 Statistiques"])

    with tab1:
        # Affichage sécurisé de l'historique
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Posez votre question..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Réflexion..."):
                    # RAG Logic
                    docs = st.session_state.vs.similarity_search(prompt, k=4)
                    context = "\n\n".join([d.page_content for d in docs])
                    
                    response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[
                            {"role": "system", "content": "Réponds en te basant uniquement sur le contexte fourni."},
                            {"role": "user", "content": f"CONTEXTE:\n{context}\n\nQUESTION: {prompt}"}
                        ]
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    with tab2:
        words = len(st.session_state.txt.split())
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="stat-card"><b>Mots</b><br><span style="font-size:1.5rem;">{words}</span></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-card"><b>Lecture</b><br><span style="font-size:1.5rem;">{max(1, words//200)} min</span></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-card"><b>Pages</b><br><span style="font-size:1.5rem;">Richesse : Élevée</span></div>', unsafe_allow_html=True)
        
        st.divider()
        st.subheader("Extrait brut")
        st.text_area("", st.session_state.txt[:2000] + "...", height=300)

st.caption(f"© {datetime.now().year} Insight PDF Pro - Kandolo Herman")
