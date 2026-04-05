import streamlit as st
from mistralai.client import MistralClient
import PyPDF2
from io import BytesIO
import os
from datetime import datetime

# --- NOUVEAUX IMPORTS LLAMA-INDEX ---
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
        font-size: 3rem; font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURATION MISTRAL VIA LLAMA-INDEX ---
def setup_engine():
    api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        st.error("Clé API Mistral manquante !")
        return
    
    # On configure LlamaIndex pour utiliser ton API Mistral pour TOUT
    # 1. Le cerveau (LLM)
    Settings.llm = MistralAI(model="mistral-large-latest", api_key=api_key, temperature=0)
    # 2. La recherche (Embedding)
    Settings.embed_model = MistralAIEmbedding(model_name="mistral-embed", api_key=api_key)

setup_engine()

# --- FONCTIONS UTILITAIRES ---
def extract_pdf_text(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-gradient">Insight PDF Pro</h1>', unsafe_allow_html=True)
st.caption(f"Développé par Herman Kandolo • {datetime.now().year}")

with st.sidebar:
    st.subheader("📤 Importation")
    uploaded_file = st.file_uploader("Choisir un PDF", type="pdf", label_visibility="collapsed")
    
    if uploaded_file:
        if 'index' not in st.session_state:
            with st.spinner("Indexation intelligente (RAG)..."):
                text = extract_pdf_text(uploaded_file)
                # Création de l'index vectoriel
                doc = Document(text=text)
                st.session_state.index = VectorStoreIndex.from_documents([doc])
                st.session_state.full_text = text
            st.success("Document indexé avec succès !")

if 'index' in st.session_state:
    tab1, tab2 = st.tabs(["💬 Chat Intelligent", "📝 Synthèse"])

    with tab1:
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Posez une question sur le document..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="✨"):
                # Création du moteur de recherche
                query_engine = st.session_state.index.as_query_engine(
                    similarity_top_k=3 # Cherche les 3 passages les plus pertinents
                )
                
                # Consigne stricte pour éviter l'hallucination
                full_prompt = (
                    f"Réponds UNIQUEMENT en te basant sur le document fourni. "
                    f"Si l'information n'est pas dedans, dis simplement que tu ne sais pas. "
                    f"Question : {prompt}"
                )
                
                response = query_engine.query(full_prompt)
                st.markdown(response.response)
                st.session_state.messages.append({"role": "assistant", "content": response.response})

    with tab2:
        if st.button("Générer un résumé global"):
            query_engine = st.session_state.index.as_query_engine()
            res = query_engine.query("Fais un résumé structuré et détaillé de ce document.")
            st.info(res.response)
else:
    st.info("Veuillez charger un PDF pour activer l'IA.")
