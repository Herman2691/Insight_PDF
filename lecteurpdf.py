import streamlit as st
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import PyPDF2
from io import BytesIO
import json
import re
from collections import Counter
from datetime import datetime
import os

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Insight PDF Pro",
    page_icon="✨",
    layout="wide"
)

# --- INTERFACE STYLE GEMINI (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
    
    html, body, [class*="ViewContainer"] {
        font-family: 'Google Sans', sans-serif;
        background-color: #ffffff;
    }

    .gemini-title {
        background: linear-gradient(70deg, #4285f4, #9b72cb, #d96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 700;
        letter-spacing: -1px;
        margin-bottom: 0px;
    }

    .gemini-subtitle {
        color: #5f6368;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }

    /* Cartes de statistiques */
    .stat-card {
        background-color: #f8f9fa;
        border: 1px solid #e1e3e1;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .stat-card:hover { transform: translateY(-5px); border-color: #4285f4; }

    /* Boutons Google Style */
    .stButton>button {
        border-radius: 24px;
        padding: 10px 24px;
        border: 1px solid #dadce0;
        background-color: #ffffff;
        color: #1a73e8;
        font-weight: 500;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #f1f3f4;
        border-color: #1a73e8;
    }

    /* Chat Input */
    .stChatInput { border-radius: 32px !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #f0f4f9; border-right: 1px solid #e1e3e1; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE TECHNIQUE ---
def extract_pdf_text(pdf_file):
    reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    text_by_page = {i + 1: p.extract_text() for i, p in enumerate(reader.pages) if p.extract_text()}
    return text_by_page

def get_full_text(text_by_page):
    return "\n\n".join([f"--- Page {p} ---\n{t}" for p, t in text_by_page.items()])

def query_mistral_client(prompt, context=""):
    try:
        api_key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
        client = MistralClient(api_key=api_key)
        
        messages = [
            ChatMessage(role="system", content="Tu es un assistant expert IA. Réponds de manière structurée."),
            ChatMessage(role="user", content=f"CONTEXTE:\n{context}\n\nQUESTION/INSTRUCTION: {prompt}")
        ]
        
        response = client.chat(model="mistral-large-latest", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur API : {str(e)}"

# --- INITIALISATION SESSION ---
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'history' not in st.session_state: st.session_state.history = []

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ✨ Insight Engine")
    uploaded_file = st.file_uploader("Charger un document", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file:
        if st.button("Analyser le PDF", use_container_width=True):
            with st.spinner("Extraction..."):
                st.session_state.pdf_data = extract_pdf_text(uploaded_file)
                st.success("Analyse terminée !")

    st.divider()
    st.caption(f"Kandolo Herman • {datetime.now().year}")

# --- INTERFACE PRINCIPALE ---
st.markdown('<h1 class="gemini-title">Insight PDF</h1>', unsafe_allow_html=True)
st.markdown('<p class="gemini-subtitle">L\'intelligence documentaire propulsée par Mistral AI</p>', unsafe_allow_html=True)

if not st.session_state.pdf_data:
    st.info("👋 Bonjour. Pour commencer, importez un document PDF dans le menu latéral.")
else:
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📝 Résumé", "✏️ Correction", "📊 Analyse"])

    full_text = get_full_text(st.session_state.pdf_data)

    # TAB 1 : CHAT
    with tab1:
        for m in st.session_state.history:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        
        if prompt := st.chat_input("Posez une question sur le document..."):
            st.session_state.history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="✨"):
                ans = query_mistral_client(prompt, full_text[:10000]) # Limite pour sécurité tokens
                st.markdown(ans)
                st.session_state.history.append({"role": "assistant", "content": ans})

    # TAB 2 : RÉSUMÉ
    with tab2:
        st.markdown("### Générer une synthèse")
        res_type = st.select_slider("Niveau de détail", options=["Court", "Moyen", "Détaillé"])
        if st.button("Lancer la rédaction"):
            with st.spinner("Rédaction en cours..."):
                prompt = f"Fais un résumé {res_type} du document avec des puces claires."
                summary = query_mistral_client(prompt, full_text[:12000])
                st.markdown(f"<div style='background:#f0f4f9; padding:20px; border-radius:15px;'>{summary}</div>", unsafe_allow_html=True)

    # TAB 3 : ORTHOGRAPHE (JSON)
    with tab3:
        st.markdown("### Vérification linguistique")
        if st.button("Scanner les erreurs"):
            with st.spinner("Analyse grammaticale..."):
                prompt = "Analyse les erreurs d'orthographe. Retourne un format JSON : {'erreurs': [{'texte': '...', 'correction': '...'}]}"
                check = query_mistral_client(prompt, full_text[:5000])
                st.code(check, language="json")

    # TAB 4 : ANALYSE LEXICALE
    with tab4:
        words = re.findall(r'\b\w+\b', full_text.lower())
        freq = Counter(words)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Mots", len(words))
        c2.metric("Mots Uniques", len(freq))
        c3.metric("Richesse", f"{len(freq)/len(words)*100:.1f}%")
        
        st.divider()
        st.subheader("Mots-clés fréquents")
        # Filtrer les mots courts
        common = [f"{w}: {c}" for w, c in freq.most_common(20) if len(w) > 4]
        st.write(", ".join(common))

st.markdown("---")
