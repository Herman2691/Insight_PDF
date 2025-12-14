import streamlit as st
from mistralai import Mistral
import PyPDF2
from io import BytesIO
import json
import re
from collections import Counter
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

# Configuration de la page
st.set_page_config(
    page_title="Insight PDF - AI Document Analysis",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design professionnel
st.markdown("""
    <style>
    /* Thème général */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    /* En-tête professionnel */
    .header-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .app-title {
        font-size: 3.5rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        letter-spacing: -1px;
    }
    
    .app-subtitle {
        font-size: 1.3rem;
        color: #a8d5ff;
        margin-top: 0.8rem;
        line-height: 1.6;
        font-weight: 300;
    }
    
    .author-info {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.2);
        color: #e0e7ff;
        font-size: 1rem;
    }
    
    .author-name {
        font-weight: 600;
        color: #ffd700;
        font-size: 1.1rem;
    }
    
    .author-title {
        color: #b8d4ff;
        font-style: italic;
        margin-left: 0.5rem;
    }
    
    /* Cartes de contenu */
    .content-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    
    /* Onglets personnalisés */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.95);
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
    }
    
    [data-testid="stSidebar"] .element-container {
        color: white;
    }
    
    /* Titres sidebar en blanc */
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .element-container p {
        color: white !important;
    }
    
    /* File uploader dans sidebar */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] label {
        color: white !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background: white !important;
        color: black !important;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: rgba(255, 255, 255, 0.8) !important;
    }
    
    /* Messages dans sidebar en blanc */
    [data-testid="stSidebar"] .stSuccess,
    [data-testid="stSidebar"] .stInfo {
        color: white !important;
        background: rgba(255, 255, 255, 0.15) !important;
        border-left-color: white !important;
    }
    
    [data-testid="stSidebar"] .stSuccess [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] .stInfo [data-testid="stMarkdownContainer"] {
        color: white !important;
    }
    
    /* Markdown dans sidebar */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: white !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
        color: white !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] ul li {
        color: white !important;
    }
    
    /* Boutons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Métriques */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #1e3c72;
        font-weight: 700;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        font-weight: 600;
        color: #1e3c72;
    }
    
    /* Messages */
    .stSuccess {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
    }
    
    .stWarning {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
    }
    
    .stError {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
    }
    
    /* Texte amélioré */
    h1, h2, h3 {
        color: #1e3c72;
        font-weight: 700;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 15px;
        color: white;
        margin-top: 3rem;
        box-shadow: 0 5px 20px rgba(0,0,0,0.2);
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de la session state
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = {}
if 'pdf_name' not in st.session_state:
    st.session_state.pdf_name = None
if 'mistral_client' not in st.session_state:
    st.session_state.mistral_client = None

def extract_pdf_text(pdf_file):
    """Extrait le texte du PDF page par page"""
    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
    text_by_page = {}
    
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text_by_page[page_num + 1] = page.extract_text()
    
    return text_by_page

def get_full_text(text_by_page):
    """Combine tout le texte du PDF"""
    return "\n\n".join([f"=== Page {page} ===\n{text}" 
                        for page, text in text_by_page.items()])

def query_mistral(client, prompt, context=""):
    """Interroge l'API Mistral AI"""
    try:
        messages = [
            {"role": "system", "content": "Tu es un assistant expert en analyse de documents. Réponds de manière précise et structurée."},
            {"role": "user", "content": f"{context}\n\n{prompt}"}
        ]
        
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur lors de la requête: {str(e)}"

def find_relevant_pages(text_by_page, answer):
    """Identifie les pages pertinentes dans la réponse"""
    pages_mentioned = []
    for page_num in text_by_page.keys():
        if f"page {page_num}" in answer.lower() or f"page{page_num}" in answer.lower():
            pages_mentioned.append(page_num)
    return sorted(set(pages_mentioned))

# En-tête professionnel
st.markdown("""
    <div class="header-container">
        <h1 class="app-title">🧠 Insight PDF</h1>
        <p class="app-subtitle">
            Analysez vos documents PDF avec l'intelligence artificielle de Mistral AI. 
            Obtenez des résumés instantanés, posez des questions, vérifiez l'orthographe 
            et explorez l'analyse sémantique en profondeur.
        </p>
        <div class="author-info">
            <span class="author-name">Kandolo Herman</span>
            <span class="author-title">• Chercheur en Intelligence Artificielle</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Sidebar - Configuration
with st.sidebar:
    st.markdown('<h2 style="color: white;">🧠 Insight PDF</h2>', unsafe_allow_html=True)
    st.markdown("### ⚙️ Configuration")
    
    # Charger la clé API uniquement depuis .env
    api_key = os.getenv("MISTRAL_API_KEY", "")
    
    if api_key:
        st.session_state.mistral_client = Mistral(api_key=api_key)
        st.success("✅ API Mistral connectée")
    else:
        st.error("❌ Clé API non trouvée")
        st.info("💡 Veuillez configurer MISTRAL_API_KEY dans le fichier .env")
    
    st.divider()
    
    st.markdown("### 📤 Charger un document")
    uploaded_file = st.file_uploader("Sélectionnez un fichier PDF", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file:
        with st.spinner("🔄 Extraction du texte en cours..."):
            st.session_state.pdf_text = extract_pdf_text(uploaded_file)
            st.session_state.pdf_name = uploaded_file.name
        
        st.success(f"✅ {len(st.session_state.pdf_text)} pages extraites")
        st.info(f"📄 **{st.session_state.pdf_name}**")
    
    st.divider()
    
    # Informations sur l'application
    st.markdown("### 📊 Capacités")
    st.markdown("""
    - 💬 Questions/Réponses IA
    - 📝 Résumés intelligents
    - ✏️ Vérification orthographique
    - 🔍 Analyse sémantique
    """)

# Vérifications préalables
if not st.session_state.mistral_client:
    st.warning("⚠️ Veuillez configurer votre clé API Mistral dans le fichier .env")
    st.stop()

if not st.session_state.pdf_text:
    st.info("📤 Veuillez charger un document PDF dans la barre latérale pour commencer l'analyse")
    st.stop()

# Onglets principaux
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Questions/Réponses",
    "📄 Résumé",
    "✏️ Orthographe",
    "📊 Analyse Lexicale"
])

# TAB 1: Questions/Réponses
with tab1:
    st.markdown("### 💬 Posez vos questions sur le document")
    st.markdown("Utilisez l'intelligence artificielle pour interroger le contenu de votre PDF")
    
    question = st.text_area(
        "Votre question:",
        placeholder="Ex: Quels sont les points principaux abordés dans ce document?",
        height=120,
        label_visibility="collapsed"
    )
    
    if st.button("🔍 Obtenir la réponse", type="primary", use_container_width=True):
        if question:
            with st.spinner("🤔 Analyse en cours..."):
                context = f"Voici le contenu du document par page:\n\n{get_full_text(st.session_state.pdf_text)}"
                prompt = f"Question: {question}\n\nRéponds de manière claire et cite les numéros de pages pertinentes."
                
                answer = query_mistral(st.session_state.mistral_client, prompt, context)
                
                st.markdown("#### 📌 Réponse:")
                st.markdown(f"<div class='content-card'>{answer}</div>", unsafe_allow_html=True)
                
                pages = find_relevant_pages(st.session_state.pdf_text, answer)
                if pages:
                    st.success(f"📄 Pages concernées: {', '.join(map(str, pages))}")
        else:
            st.warning("⚠️ Veuillez entrer une question")

# TAB 2: Résumé
with tab2:
    st.markdown("### 📄 Résumé automatique du document")
    st.markdown("Générez un résumé intelligent adapté à vos besoins")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        summary_type = st.radio(
            "Type de résumé:",
            ["Court", "Moyen", "Détaillé"],
            label_visibility="collapsed"
        )
        
        st.markdown(f"""
        **{summary_type}**
        - Court: 3-5 phrases
        - Moyen: 2-3 paragraphes
        - Détaillé: Analyse complète
        """)
    
    with col2:
        if st.button("📝 Générer le résumé", type="primary", use_container_width=True):
            with st.spinner("⏳ Génération du résumé..."):
                length_instruction = {
                    "Court": "en 3-5 phrases",
                    "Moyen": "en 2-3 paragraphes",
                    "Détaillé": "de manière détaillée avec les points clés"
                }
                
                context = get_full_text(st.session_state.pdf_text)
                prompt = f"Fais un résumé {length_instruction[summary_type]} de ce document. Structure ton résumé de manière claire."
                
                summary = query_mistral(st.session_state.mistral_client, prompt, context)
                
                st.markdown("#### 📋 Résumé:")
                st.markdown(f"<div class='content-card'>{summary}</div>", unsafe_allow_html=True)
    
    # Statistiques du document
    st.divider()
    st.markdown("### 📊 Statistiques du document")
    
    col1, col2, col3 = st.columns(3)
    
    total_text = get_full_text(st.session_state.pdf_text)
    word_count = len(total_text.split())
    char_count = len(total_text)
    
    col1.metric("📄 Pages", len(st.session_state.pdf_text))
    col2.metric("📝 Mots", f"{word_count:,}")
    col3.metric("🔤 Caractères", f"{char_count:,}")

# TAB 3: Vérification Orthographique
with tab3:
    st.markdown("### ✏️ Vérification orthographique et grammaticale")
    st.markdown("Détectez et corrigez les erreurs dans votre document")
    
    if st.button("🔍 Analyser l'orthographe", type="primary", use_container_width=True):
        with st.spinner("⏳ Vérification en cours..."):
            results = []
            
            for page_num, text in st.session_state.pdf_text.items():
                prompt = f"""Analyse ce texte et identifie UNIQUEMENT les erreurs d'orthographe et de grammaire réelles.
                
Texte à analyser:
{text}

Réponds au format JSON:
{{
    "erreurs": [
        {{"texte": "mot ou phrase erronée", "correction": "correction proposée", "type": "orthographe/grammaire"}}
    ],
    "nombre_erreurs": nombre
}}

Si aucune erreur, retourne {{"erreurs": [], "nombre_erreurs": 0}}"""
                
                response = query_mistral(st.session_state.mistral_client, prompt)
                
                try:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        if result.get('nombre_erreurs', 0) > 0:
                            results.append({
                                'page': page_num,
                                'erreurs': result['erreurs']
                            })
                except:
                    pass
            
            if results:
                st.warning(f"⚠️ {len(results)} page(s) contient/contiennent des erreurs")
                
                for result in results:
                    with st.expander(f"📄 Page {result['page']} - {len(result['erreurs'])} erreur(s)"):
                        for i, erreur in enumerate(result['erreurs'], 1):
                            st.markdown(f"**{i}. {erreur.get('type', 'Erreur').capitalize()}**")
                            col1, col2 = st.columns(2)
                            col1.markdown(f"❌ *{erreur['texte']}*")
                            col2.markdown(f"✅ *{erreur['correction']}*")
                            st.divider()
            else:
                st.success("✅ Aucune erreur détectée dans le document!")

# TAB 4: Analyse Lexicale & Sémantique
with tab4:
    st.markdown("### 📊 Analyse lexicale et sémantique")
    st.markdown("Explorez en profondeur le contenu et la structure de votre document")
    
    if st.button("📈 Lancer l'analyse complète", type="primary", use_container_width=True):
        with st.spinner("🔄 Analyse approfondie en cours..."):
            full_text = get_full_text(st.session_state.pdf_text)
            
            # Analyse lexicale basique
            words = re.findall(r'\b\w+\b', full_text.lower())
            word_freq = Counter(words)
            
            # Analyse Mistral
            prompt = """Analyse ce document et fournis:
            1. Les thèmes principaux abordés
            2. Le ton général (formel, informel, technique, etc.)
            3. Les mots-clés les plus importants (10 minimum)
            4. Le type de document (article, rapport, étude, etc.)
            5. Le public cible probable
            
            Structure ta réponse clairement avec des sections."""
            
            analysis = query_mistral(st.session_state.mistral_client, prompt, full_text)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 📊 Statistiques lexicales")
                
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric("🔤 Vocabulaire unique", len(word_freq))
                metric_col2.metric("📝 Mots totaux", len(words))
                
                st.metric("💎 Richesse lexicale", f"{len(word_freq)/len(words)*100:.1f}%")
                
                st.markdown("#### 🔤 Mots les plus fréquents")
                top_words = word_freq.most_common(15)
                for word, count in top_words:
                    if len(word) > 3:
                        st.text(f"• {word}: {count} fois")
            
            with col2:
                st.markdown("#### 🧠 Analyse sémantique (Mistral AI)")
                st.markdown(f"<div class='content-card'>{analysis}</div>", unsafe_allow_html=True)
            
            # Distribution par page
            st.divider()
            st.markdown("### 📄 Distribution du contenu par page")
            
            page_stats = []
            for page_num, text in st.session_state.pdf_text.items():
                page_words = len(text.split())
                page_stats.append({"Page": page_num, "Mots": page_words})
            
            st.dataframe(page_stats, use_container_width=True)

# Footer professionnel
st.markdown("""
    <div class="footer">
        <h3 style="color: white; margin-bottom: 1rem;">🧠 Insight PDF</h3>
        <p style="margin: 0.5rem 0;">Powered by <strong>Mistral AI</strong> • Développé avec ❤️ en Streamlit</p>
        <p style="margin: 0.5rem 0; color: #ffd700;">Kandolo Herman • Chercheur en Intelligence Artificielle</p>
        <p style="margin-top: 1rem; font-size: 0.9rem; color: #b8d4ff;">© 2024 • Tous droits réservés</p>
    </div>
""", unsafe_allow_html=True)