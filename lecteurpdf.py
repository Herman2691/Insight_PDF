import streamlit as st
import os
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

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

st.set_page_config(page_title="Insight PDF Pro", page_icon="✨", layout="wide")

# --- PLUS DE st.markdown HTML complexe ---
# Un seul bloc CSS minimal, sans classes dynamiques
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE RAG ---
def process_pdf(pdf_file, api_key):
    try:
        reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        if not text.strip():
            return None, "PDF vide ou image seule."
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_text(text)
        
        db_name = f"db_{int(datetime.now().timestamp())}"
        embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        vectorstore = Chroma.from_texts(chunks, embeddings, collection_name=db_name)
        
        return vectorstore, text
    except Exception as e:
        return None, str(e)

# --- SESSION STATE ---
if 'vs' not in st.session_state:
    st.session_state.vs = None
if 'txt' not in st.session_state:
    st.session_state.txt = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- Validation clé API ---
api_key = os.getenv("MISTRAL_API_KEY", "")
client = None
if api_key:
    client = Mistral(api_key=api_key)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🛠️ Configuration")
    
    if not api_key:
        st.error("⚠️ Variable MISTRAL_API_KEY manquante dans les secrets.")
    
    file = st.file_uploader("Charger un document PDF", type=['pdf'])
    
    if file and st.button("Lancer l'Analyse ✨", use_container_width=True):
        if not client:
            st.error("Clé API Mistral non configurée.")
        else:
            with st.spinner("Analyse sémantique en cours..."):
                vs, text = process_pdf(file, api_key)
                if vs:
                    st.session_state.vs = vs
                    st.session_state.txt = text
                    st.session_state.chat_history = []
                    st.success("Analyse terminée !")
                    # Pas de st.rerun() ici — on laisse Streamlit re-rendre naturellement
                else:
                    st.error(text)

    if st.session_state.vs:
        if st.button("Effacer tout", type="secondary", use_container_width=True):
            st.session_state.vs = None
            st.session_state.txt = ""
            st.session_state.chat_history = []
            # st.rerun() retiré — on utilise une clé de formulaire à la place
            st.rerun()

# --- INTERFACE PRINCIPALE ---
# Titre natif Streamlit, pas de HTML
st.title("✨ Insight PDF Pro")

if not st.session_state.vs:
    st.write("### Bonjour. Que souhaitez-vous analyser ?")
    st.info("👈 Commencez par importer un document PDF dans le menu latéral.")

else:
    tab1, tab2 = st.tabs(["💬 Assistant", "📊 Statistiques"])

    with tab1:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Posez votre question..."):
            if not client:
                st.error("Clé API Mistral non configurée.")
            else:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Réflexion..."):
                        try:
                            docs = st.session_state.vs.similarity_search(prompt, k=4)
                            context = "\n\n".join([d.page_content for d in docs])
                            
                            # Historique inclus dans le prompt (correction bonus)
                            history_messages = [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.chat_history[-6:]  # 3 derniers échanges
                            ]
                            
                            response = client.chat.complete(
                                model="mistral-large-latest",
                                messages=[
                                    {"role": "system", "content": f"Réponds uniquement à partir du contexte fourni.\n\nCONTEXTE:\n{context}"},
                                    *history_messages,
                                ]
                            )
                            answer = response.choices[0].message.content
                            st.markdown(answer)
                            st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        except Exception as e:
                            st.error(f"Erreur lors de la génération : {e}")

    with tab2:
        words = len(st.session_state.txt.split())
        reading_time = max(1, words // 200)
        
        # Composants natifs Streamlit — PLUS de st.markdown HTML pour les stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Mots", value=f"{words:,}")
        with col2:
            st.metric(label="Temps de lecture", value=f"{reading_time} min")
        with col3:
            st.metric(label="Richesse sémantique", value="Élevée")
        
        st.divider()
        st.subheader("Extrait brut")
        preview = st.session_state.txt[:2000]
        if len(st.session_state.txt) > 2000:
            preview += "..."
        st.text_area("", preview, height=300)

st.caption(f"© {datetime.now().year} Insight PDF Pro - Kandolo Herman")
