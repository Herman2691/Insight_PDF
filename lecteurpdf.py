import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

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

load_dotenv()

# --- CONFIGURATION (Sans polices externes pour la stabilité) ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

# --- CSS MINIMALISTE (Style Gemini sans fioritures risquées) ---
st.markdown("""
    <style>
    /* On utilise les polices système pour éviter l'erreur removeChild */
    html, body, [class*="ViewContainer"] {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    .gemini-gradient {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        font-size: 2.5rem;
    }
    .stChatFloatingInputContainer { background-color: rgba(255,255,255,0) !important; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE IA ---
def process_pdf(pdf_file, api_key):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        full_text = "\n".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
        if not full_text.strip(): return None, "PDF illisible."
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_text(full_text)
        
        # Utilisation d'un ID unique pour éviter les conflits de dossier Chroma
        db_id = f"db_{int(datetime.now().timestamp())}"
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(
            texts=chunks, 
            embedding=embeddings, 
            collection_name=db_id
        )
        return vectorstore, full_text
    except Exception as e:
        return None, str(e)

# --- SESSION STATE ---
if 'vs' not in st.session_state: st.session_state.vs = None
if 'txt' not in st.session_state: st.session_state.txt = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("📁 Documents")
    uploaded_file = st.file_uploader("Charger un PDF", type=['pdf'])
    
    if uploaded_file and st.button("Analyser maintenant", use_container_width=True):
        with st.status("Traitement du document...", expanded=True) as status:
            vs, text = process_pdf(uploaded_file, api_key)
            if vs:
                st.session_state.vs = vs
                st.session_state.txt = text
                status.update(label="Analyse terminée !", state="complete")
            else:
                st.error(text)

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF Pro</h1>', unsafe_allow_html=True)

if not st.session_state.vs:
    st.write("### Bonjour. Comment puis-je vous aider ?")
    st.info("Importez un document dans le menu de gauche pour commencer l'analyse.")
else:
    # Affichage de l'historique du chat pour éviter les sauts de page
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Zone de saisie
    query = st.chat_input("Posez votre question sur le PDF...")
    
    if query:
        # Afficher le message utilisateur
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # Réponse Assistant
        with st.chat_message("assistant"):
            with st.spinner("Recherche dans le document..."):
                try:
                    docs = st.session_state.vs.similarity_search(query, k=4)
                    context = "\n\n".join([d.page_content for d in docs])
                    
                    resp = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[
                            {"role": "system", "content": "Expert en analyse de documents PDF."},
                            {"role": "user", "content": f"CONTEXTE:\n{context}\n\nQUESTION: {query}"}
                        ]
                    )
                    answer = resp.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Erreur de réponse: {e}")

# Footer simplifié pour la stabilité
st.write("---")
st.caption(f"© {datetime.now().year} Insight PDF Pro - Kandolo Herman")
