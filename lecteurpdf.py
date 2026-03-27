import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

# --- FIX CHROMADB POUR LE CLOUD ---
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

# --- CONFIGURATION TECHNIQUE ---
st.set_page_config(page_title="Insight PDF", page_icon="✨", layout="wide")

# --- CSS STABLE (Couleurs & Arrondis uniquement, pas de structure HTML) ---
st.markdown("""
    <style>
    /* Couleurs inspirées de Gemini */
    :root {
        --gemini-blue: #1a73e8;
    }
    .stApp {
        background-color: #ffffff;
    }
    /* Style des boutons et inputs */
    div.stButton > button {
        border-radius: 20px;
        border: 1px solid #dadce0;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        border-color: var(--gemini-blue);
        color: var(--gemini-blue);
    }
    /* Masquer le menu Streamlit pour plus de propreté */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE DE TRAITEMENT ---
def get_pdf_text(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"
    return text

def create_vectorstore(text, api_key):
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_text(text)
    embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
    # Utilisation d'un dossier temporaire unique pour éviter les conflits d'accès
    return Chroma.from_texts(chunks, embeddings)

# --- INITIALISATION DE L'ÉTAT ---
if 'processed' not in st.session_state:
    st.session_state.processed = False
    st.session_state.vectorstore = None
    st.session_state.full_text = ""
    st.session_state.messages = []

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- SIDEBAR : FONCTIONNALITÉS ---
with st.sidebar:
    st.title("✨ Insight PDF")
    st.caption("Analyseur RAG Intelligent")
    
    uploaded_file = st.file_uploader("Document PDF", type="pdf", help="Chargez votre document ici")
    
    if uploaded_file and not st.session_state.processed:
        if st.button("Lancer l'analyse", use_container_width=True, type="primary"):
            with st.spinner("Indexation en cours..."):
                text = get_pdf_text(uploaded_file)
                if text:
                    st.session_state.full_text = text
                    st.session_state.vectorstore = create_vectorstore(text, api_key)
                    st.session_state.processed = True
                    st.rerun()

    if st.session_state.processed:
        if st.button("Réinitialiser", use_container_width=True):
            st.session_state.processed = False
            st.session_state.messages = []
            st.rerun()

# --- INTERFACE PRINCIPALE ---
if not st.session_state.processed:
    st.title("Bonjour.")
    st.subheader("Posez des questions à vos documents complexes.")
    st.write("Veuillez charger un fichier PDF dans la barre latérale pour commencer.")
    
    # Présentation visuelle simple
    col1, col2, col3 = st.columns(3)
    col1.help("Recherche sémantique précise")
    col2.help("Analyse de données textuelles")
    col3.help("Résumé et synthèse")
else:
    # Onglets pour séparer les fonctionnalités sans casser le DOM
    tab_chat, tab_stats = st.tabs(["💬 Assistant Gemini", "📊 Statistiques"])

    with tab_chat:
        # Affichage des messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Input utilisateur
        if prompt := st.chat_input("Demandez une analyse..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Réflexion..."):
                    # Récupération contexte
                    docs = st.session_state.vectorstore.similarity_search(prompt, k=3)
                    context = "\n".join([d.page_content for d in docs])
                    
                    # Appel API
                    response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[
                            {"role": "system", "content": "Tu es un assistant analytique. Utilise le contexte fourni."},
                            {"role": "user", "content": f"Contexte: {context}\n\nQuestion: {prompt}"}
                        ]
                    )
                    answer = response.choices[0].message.content
                    st.write(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

    with tab_stats:
        st.subheader("Analyse du document")
        words = st.session_state.full_text.split()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Nombre de mots", len(words))
        c2.metric("Temps de lecture", f"{max(1, len(words)//200)} min")
        c3.metric("Caractères", len(st.session_state.full_text))
        
        st.divider()
        st.write("🔍 **Aperçu du texte extrait :**")
        st.text_area("", st.session_state.full_text[:1500] + "...", height=300)

# Footer
st.markdown(f"---")
st.caption(f"Développé par Kandolo Herman • {datetime.now().year}")
