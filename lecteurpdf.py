import streamlit as st
import PyPDF2
from io import BytesIO
import json
import re
from collections import Counter
from datetime import datetime
import os
from gtts import gTTS
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# --- FIX POUR PERMISSION ERROR (NLTK) ---
import nltk
nltk_data_dir = os.path.join(os.getcwd(), "nltk_data")
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)
nltk.download('punkt_tab', download_dir=nltk_data_dir)

# --- IMPORTS MISTRAL ET LLAMA-INDEX ---
# On utilise l'import moderne pour éviter l'erreur de client
try:
    from mistralai import Mistral as MistralClient
except ImportError:
    from mistralai.client import MistralClient

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.llms.mistralai import MistralAI
from llama_index.embeddings.mistralai import MistralAIEmbedding

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    html, body, [class*="ViewContainer"] { font-family: 'Google Sans', sans-serif; }
    .gemini-gradient {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 700; margin-bottom: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURATION MOTEURS ---
def setup_engines():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if api_key:
        Settings.llm = MistralAI(model="mistral-large-latest", api_key=api_key, temperature=0)
        Settings.embed_model = MistralAIEmbedding(model_name="mistral-embed", api_key=api_key)
        # On évite d'instancier MistralClient ici si non utilisé directement
        return api_key
    return None

api_key_val = setup_engines()

# ... (Garde tes fonctions extract_pdf_data et create_pptx ici)

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF Pro</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf")
    if uploaded_file:
        if 'index' not in st.session_state:
            with st.spinner("Indexation intelligente..."):
                reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
                full_text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                st.session_state.full_text = full_text
                doc = Document(text=full_text)
                st.session_state.index = VectorStoreIndex.from_documents([doc])
            st.success("Prêt !")

# --- ONGLETS ---
if 'index' in st.session_state:
    tabs = st.tabs(["💬 Chat", "📝 Synthèse", "📊 Analyse", "🔊 Audio", "🎯 Présentation"])
    
    # Reste de ton code (Chat, Synthèse, etc.) tel quel...
    # Dans l'onglet Présentation, garde bien le nettoyage JSON :
    # start, end = raw.find('{'), raw.rfind('}') + 1
