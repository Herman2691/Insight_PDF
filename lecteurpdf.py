"""
Insight PDF - Analyseur de Documents Intelligent (Version Pro)
Développé par Kandolo Herman - Chercheur en IA
"""

import streamlit as st
from mistralai import Mistral
import PyPDF2
from io import BytesIO
import json
import re
from collections import Counter
from dotenv import load_dotenv
import os
from datetime import datetime

# Charger les variables d'environnement
load_dotenv()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Insight PDF - AI Document Analysis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN PREMIUM (SYSTÈME DE DESIGN GOOGLE/GEMINI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Inter:wght@300;400;500;600&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    h1, h2, h3, .google-font { font-family: 'Google Sans', sans-serif; }
    
    .stApp { background-color: #f8f9fa; }

    /* En-tête */
    .header-gradient {
        background: linear-gradient(135deg, #0b57d0 0%, #1e3c72 100%);
        padding: 3rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 10px 30px rgba(11, 87, 208, 0.2);
    }
    
    /* Cartes Statistiques */
    .stat-card {
        background: white;
        padding: 24px;
        border-radius: 20px;
        border: 1px solid #e3e3e3;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stat-card:hover { 
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0,0,0,0.05);
        border-color: #0b57d0;
    }
    .stat-val { font-size: 2.5rem; font-weight: 700; color: #0b57d0; }
    .stat-label { font-size: 1rem; color: #5f6368; font-weight: 500; }

    /* Onglets */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border: 1px solid #e3e3e3;
        border-radius: 12px 12px 0 0;
        padding: 10px 20px;
        font-weight: 500;
        color: #5f6368;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e8f0fe !important;
        color: #0b57d0 !important;
        border-bottom: 2px solid #0b57d0 !important;
    }

    /* Sections d'Audit */
    .audit-box {
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 15px;
        color: white !important;
    }
    .audit-tone { background-color: #1a73e8; }
    .audit-clarity { background-color: #34a853; }
    .audit-errors { background-color: #d93025; }
    .audit-suggestions { background-color: #f9ab00; }
    
    .audit-box h4 { color: white !important; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 5px; }
    .audit-box p, .audit-box li { color: white !important; font-size: 0.95rem; }

    /* Boutons */
    .stButton > button {
        background-color: #0b57d0 !important;
        color: white !important;
        border-radius: 100px !important;
        padding: 10px 24px !important;
        font-weight: 500;
        border: none !important;
        transition: all 0.2s;
    }
    .stButton > button:hover { opacity: 0.9; transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# --- LOGIQUE D'EXTRACTION ET IA ---

def extract_pdf_text(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text_by_page = {}
        for page_num in range(len(pdf_reader.pages)):
            content = pdf_reader.pages[page_num].extract_text()
            text_by_page[page_num + 1] = content if content else "[Page sans texte extractible]"
        return text_by_page
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF : {str(e)}")
        return {}

def get_full_text(text_by_page):
    return "\n\n".join([f"--- Page {p} ---\n{t}" for p, t in text_by_page.items()])

def query_mistral(client, prompt, context="", system_msg="Tu es un expert en analyse de documents."):
    try:
        messages = [
            {"role": "system", "content": f"{system_msg} Réponds de manière structurée en utilisant le Markdown."},
            {"role": "user", "content": f"DOCUMENT :\n{context[:15000]}\n\nINSTRUCTION : {prompt}"}
        ]
        response = client.chat.complete(model="mistral-large-latest", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur de communication avec l'IA : {str(e)}"

# --- INITIALISATION ---

if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = {}
if 'mistral_client' not in st.session_state:
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if api_key:
        st.session_state.mistral_client = Mistral(api_key=api_key)

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.markdown("<h2 class='google-font'>⚙️ Panneau de contrôle</h2>", unsafe_allow_html=True)
    
    if not st.session_state.mistral_client:
        st.error("🔑 Clé API Mistral manquante dans le .env")
    else:
        st.success("✅ Connexion IA établie")
        
    st.markdown("---")
    st.subheader("📤 Document à analyser")
    uploaded_file = st.file_uploader("Déposez votre PDF", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file:
        if 'pdf_name' not in st.session_state or st.session_state.pdf_name != uploaded_file.name:
            with st.spinner("Analyse du document..."):
                st.session_state.pdf_text = extract_pdf_text(uploaded_file)
                st.session_state.pdf_name = uploaded_file.name
        st.success(f"📄 {st.session_state.pdf_name} chargé")

# --- INTERFACE PRINCIPALE ---

st.markdown(f"""
    <div class="header-gradient">
        <h1 style="margin:0; font-family:'Google Sans';">🧠 Insight PDF Pro</h1>
        <p style="opacity:0.9; font-size:1.2rem; margin-top:10px;">Intelligence Sémantique & Analyse Documentaire de Haute Précision</p>
        <div style="margin-top:25px; padding-top:15px; border-top:1px solid rgba(255,255,255,0.2);">
            <span style="background:rgba(255,255,255,0.2); padding:5px 15px; border-radius:50px; font-size:0.9rem;">
                👨‍🔬 Kandolo Herman • Chercheur en IA
            </span>
        </div>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.pdf_text:
    st.info("💡 Pour commencer, veuillez charger un document PDF via le panneau latéral à gauche.")
    st.stop()

# ONGLETS
t1, t2, t3, t4 = st.tabs([
    "💬 Assistant Intelligent", 
    "📝 Synthèse Executive", 
    "📊 Analyse de Données", 
    "🔍 Audit Qualité"
])

# --- TAB 1 : ASSISTANT ---
with t1:
    st.markdown("### 💬 Interroger le document")
    user_q = st.text_area("Que souhaitez-vous savoir ?", placeholder="Ex: Résume les obligations légales citées en page 3...", height=120)
    
    if st.button("Lancer l'interrogation", type="primary"):
        if user_q:
            with st.spinner("L'IA parcourt les pages..."):
                ans = query_mistral(st.session_state.mistral_client, user_q, get_full_text(st.session_state.pdf_text))
                st.markdown("---")
                st.markdown(ans)
        else:
            st.warning("Veuillez saisir une question.")

# --- TAB 2 : RÉSUMÉ ---
with t2:
    st.markdown("### 📝 Générateur de Synthèse")
    col_r1, col_r2 = st.columns([2, 1])
    with col_r2:
        format_res = st.selectbox("Style de sortie", ["Points clés", "Paragraphes", "Tableau récapitulatif"])
        r_length = st.select_slider("Précision", options=["Rapide", "Standard", "Détaillé"])
    
    with col_r1:
        if st.button("Générer la synthèse executive"):
            with st.spinner("Rédaction en cours..."):
                prompt = f"Rédige un résumé {r_length} sous forme de {format_res}. Sois très précis."
                res = query_mistral(st.session_state.mistral_client, prompt, get_full_text(st.session_state.pdf_text))
                st.info(res)

# --- TAB 3 : STATS ---
with t3:
    full_txt = get_full_text(st.session_state.pdf_text)
    words = re.findall(r'\b\w+\b', full_txt.lower())
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Pages</div><div class="stat-val">{len(st.session_state.pdf_text)}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Mots</div><div class="stat-val">{len(words)}</div></div>', unsafe_allow_html=True)
    with c3:
        unique_w = len(Counter(words))
        st.markdown(f'<div class="stat-card"><div class="stat-label">Vocabulaire</div><div class="stat-val">{unique_w}</div></div>', unsafe_allow_html=True)
    with c4:
        richness = f"{(unique_w/len(words)*100):.1f}%" if words else "0%"
        st.markdown(f'<div class="stat-card"><div class="stat-label">Richesse</div><div class="stat-val">{richness}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📈 Top thématiques détectées")
    # Filtrage des stopwords simples
    freq = Counter([w for w in words if len(w) > 4]).most_common(12)
    cols = st.columns(3)
    for i, (w, c) in enumerate(freq):
        cols[i % 3].markdown(f"🔹 **{w.upper()}** : {c} occurrences")

# --- TAB 4 : AUDIT ---
with t4:
    st.markdown("### 🔍 Audit Sémantique & Structurel")
    if st.button("Démarrer l'audit profond"):
        with st.spinner("Analyse de la qualité du contenu..."):
            prompt = """Analyse le document selon 4 critères et renvoie un JSON (format strict):
            {"ton": "description du ton", "clarte": "analyse de la clarte", "erreurs": "erreurs ou faiblesses", "suggestions": "pistes d'amélioration"}"""
            raw_audit = query_mistral(st.session_state.mistral_client, prompt, get_full_text(st.session_state.pdf_text), "Tu es un auditeur de documents. Réponds en JSON uniquement.")
            
            try:
                # Nettoyage pour extraction JSON
                json_str = re.search(r'\{.*\}', raw_audit, re.DOTALL).group()
                data = json.loads(json_str)
                
                # Affichage formaté
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.markdown(f'<div class="audit-box audit-tone"><h4>🎭 Ton & Style</h4><p>{data["ton"]}</p></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="audit-box audit-errors"><h4>🚩 Faiblesses & Erreurs</h4><p>{data["erreurs"]}</p></div>', unsafe_allow_html=True)
                with col_a2:
                    st.markdown(f'<div class="audit-box audit-clarity"><h4>✨ Clarté & Lisibilité</h4><p>{data["clarte"]}</p></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="audit-box audit-suggestions"><h4>💡 Améliorations</h4><p>{data["suggestions"]}</p></div>', unsafe_allow_html=True)
            except:
                st.error("L'IA n'a pas pu structurer l'audit. Voici la réponse brute :")
                st.write(raw_audit)

# --- PIED DE PAGE ---
st.markdown(f"""
    <div style="text-align:center; padding:40px; color:#5f6368; font-size:0.9rem; border-top:1px solid #e3e3e3; margin-top:50px;">
        <b>Insight PDF Pro</b> • {datetime.now().year} • Système Expert d'Analyse Documentaire<br>
        Propulsé par <b>Mistral AI Large</b> & Streamlit
    </div>
""", unsafe_allow_html=True)
