import streamlit as st
import os
import re
from io import BytesIO
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

# --- CORRECTIF POUR CHROMADB ---
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

# --- CONFIGURATION ---
st.set_page_config(page_title="Insight PDF", page_icon="✨", layout="wide")

# --- CSS STABILISÉ (Moins intrusif pour éviter removeChild) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="ViewContainer"] {
        font-family: 'Google Sans', sans-serif;
    }

    .gemini-title {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0px;
    }

    /* Style des cartes sans casser le DOM */
    .stat-box {
        background-color: #f0f4f9;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e1e3e1;
    }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS (Logique RAG) ---
def process_pdf_to_rag(pdf_file, api_key):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        full_text = "\n".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
        if not full_text.strip(): return None, "PDF vide."
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_text(full_text)
        
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(texts=chunks, embedding=embeddings)
        return vectorstore, full_text
    except Exception as e:
        return None, str(e)

def query_with_context(client, vectorstore, question):
    docs = vectorstore.similarity_search(question, k=4)
    context = "\n\n".join([doc.page_content for doc in docs])
    messages = [
        {"role": "system", "content": "Tu es un expert en analyse. Réponds de façon concise."},
        {"role": "user", "content": f"Contexte: {context}\n\nQuestion: {question}"}
    ]
    response = client.chat.complete(model="mistral-large-latest", messages=messages)
    return response.choices[0].message.content

# --- GESTION ÉTAT ---
if 'vs' not in st.session_state: st.session_state.vs = None
if 'txt' not in st.session_state: st.session_state.txt = ""

api_key = os.getenv("MISTRAL_API_KEY", "")
client = Mistral(api_key=api_key) if api_key else None

# --- SIDEBAR ---
with st.sidebar:
    st.title("Settings")
    file = st.file_uploader("Upload PDF", type=['pdf'])
    if file and st.button("Lancer l'analyse"):
        with st.spinner("Analyse en cours..."):
            vs, txt = process_pdf_to_rag(file, api_key)
            st.session_state.vs = vs
            st.session_state.txt = txt
            st.success("Prêt !")

# --- MAIN UI ---
st.markdown('<h1 class="gemini-title">Insight PDF</h1>', unsafe_allow_html=True)

if not st.session_state.vs:
    st.info("Veuillez charger un document pour commencer.")
else:
    t1, t2 = st.tabs(["💬 Assistant", "📊 Stats"])
    
    with t1:
        # L'utilisation de containers dédiés évite les erreurs de rendu
        chat_placeholder = st.container()
        query = st.chat_input("Posez votre question...")
        
        if query:
            with st.chat_message("user"):
                st.write(query)
            with st.chat_message("assistant"):
                # On utilise un spinner Streamlit standard, pas de HTML custom ici
                with st.spinner("Réflexion..."):
                    res = query_with_context(client, st.session_state.vs, query)
                    st.markdown(res)

    with t2:
        words = len(st.session_state.txt.split())
        c1, c2 = st.columns(2)
        c1.metric("Mots", words)
        c2.metric("Lecture", f"{max(1, words//200)} min")
        st.text_area("Texte brut", st.session_state.txt[:1000], height=200)
