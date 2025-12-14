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

# En-tête avec container natif Streamlit
st.title("🧠 Insight PDF")
st.subheader("Analysez vos documents PDF avec l'intelligence artificielle")

st.info("""
**À propos de l'application:**  
Obtenez des résumés instantanés, posez des questions, vérifiez l'orthographe 
et explorez l'analyse sémantique en profondeur grâce à Mistral AI.

**Développé par:** Kandolo Herman • Chercheur en Intelligence Artificielle
""")

st.divider()

# Sidebar
with st.sidebar:
    st.title("🧠 Insight PDF")
    st.divider()
    
    st.subheader("⚙️ Configuration")
    
    api_key = os.getenv("MISTRAL_API_KEY", "")
    
    if api_key:
        st.session_state.mistral_client = Mistral(api_key=api_key)
        st.success("✅ API Mistral connectée")
    else:
        st.error("❌ Clé API non trouvée")
        st.info("💡 Veuillez configurer MISTRAL_API_KEY dans le fichier .env")
    
    st.divider()
    
    st.subheader("📤 Charger un document")
    uploaded_file = st.file_uploader("Sélectionnez un fichier PDF", type=['pdf'])
    
    if uploaded_file:
        with st.spinner("🔄 Extraction du texte..."):
            st.session_state.pdf_text = extract_pdf_text(uploaded_file)
            st.session_state.pdf_name = uploaded_file.name
        
        st.success(f"✅ {len(st.session_state.pdf_text)} pages extraites")
        st.info(f"📄 **{st.session_state.pdf_name}**")
    
    st.divider()
    
    st.subheader("📊 Capacités")
    st.markdown("""
    - 💬 Questions/Réponses IA
    - 📝 Résumés intelligents
    - ✏️ Vérification orthographique
    - 🔍 Analyse sémantique
    """)

# Vérifications
if not st.session_state.mistral_client:
    st.warning("⚠️ Veuillez configurer votre clé API Mistral dans le fichier .env")
    st.stop()

if not st.session_state.pdf_text:
    st.info("📤 Veuillez charger un document PDF dans la barre latérale pour commencer l'analyse")
    st.stop()

# Onglets
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Questions/Réponses",
    "📄 Résumé",
    "✏️ Orthographe",
    "📊 Analyse Lexicale"
])

# TAB 1: Questions/Réponses
with tab1:
    st.header("💬 Posez vos questions sur le document")
    st.caption("Utilisez l'intelligence artificielle pour interroger le contenu de votre PDF")
    
    question = st.text_area(
        "Votre question:",
        placeholder="Ex: Quels sont les points principaux abordés dans ce document?",
        height=120
    )
    
    if st.button("🔍 Obtenir la réponse", type="primary", use_container_width=True):
        if question:
            with st.spinner("🤔 Analyse en cours..."):
                context = f"Voici le contenu du document par page:\n\n{get_full_text(st.session_state.pdf_text)}"
                prompt = f"Question: {question}\n\nRéponds de manière claire et cite les numéros de pages pertinentes."
                
                answer = query_mistral(st.session_state.mistral_client, prompt, context)
                
                st.subheader("📌 Réponse:")
                st.write(answer)
                
                pages = find_relevant_pages(st.session_state.pdf_text, answer)
                if pages:
                    st.success(f"📄 Pages concernées: {', '.join(map(str, pages))}")
        else:
            st.warning("⚠️ Veuillez entrer une question")

# TAB 2: Résumé
with tab2:
    st.header("📄 Résumé automatique du document")
    st.caption("Générez un résumé intelligent adapté à vos besoins")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        summary_type = st.radio(
            "Type de résumé:",
            ["Court", "Moyen", "Détaillé"]
        )
        
        st.info("""
        **Description:**
        - **Court**: 3-5 phrases
        - **Moyen**: 2-3 paragraphes
        - **Détaillé**: Analyse complète
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
                
                st.subheader("📋 Résumé:")
                st.write(summary)
    
    st.divider()
    st.subheader("📊 Statistiques du document")
    
    col1, col2, col3 = st.columns(3)
    
    total_text = get_full_text(st.session_state.pdf_text)
    word_count = len(total_text.split())
    char_count = len(total_text)
    
    col1.metric("📄 Pages", len(st.session_state.pdf_text))
    col2.metric("📝 Mots", f"{word_count:,}")
    col3.metric("🔤 Caractères", f"{char_count:,}")

# TAB 3: Vérification Orthographique
with tab3:
    st.header("✏️ Vérification orthographique et grammaticale")
    st.caption("Détectez et corrigez les erreurs dans votre document")
    
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
                            with col1:
                                st.error(f"❌ {erreur['texte']}")
                            with col2:
                                st.success(f"✅ {erreur['correction']}")
                            st.divider()
            else:
                st.success("✅ Aucune erreur détectée dans le document!")

# TAB 4: Analyse Lexicale
with tab4:
    st.header("📊 Analyse lexicale et sémantique")
    st.caption("Explorez en profondeur le contenu et la structure de votre document")
    
    if st.button("📈 Lancer l'analyse complète", type="primary", use_container_width=True):
        with st.spinner("🔄 Analyse approfondie en cours..."):
            full_text = get_full_text(st.session_state.pdf_text)
            
            # Analyse lexicale
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
                st.subheader("📊 Statistiques lexicales")
                
                st.metric("🔤 Vocabulaire unique", len(word_freq))
                st.metric("📝 Mots totaux", len(words))
                st.metric("💎 Richesse lexicale", f"{len(word_freq)/len(words)*100:.1f}%")
                
                st.divider()
                st.markdown("**🔤 Mots les plus fréquents**")
                top_words = word_freq.most_common(15)
                for word, count in top_words:
                    if len(word) > 3:
                        st.text(f"• {word}: {count} fois")
            
            with col2:
                st.subheader("🧠 Analyse sémantique (Mistral AI)")
                st.write(analysis)
            
            st.divider()
            st.subheader("📄 Distribution du contenu par page")
            
            page_stats = []
            for page_num, text in st.session_state.pdf_text.items():
                page_words = len(text.split())
                page_stats.append({"Page": page_num, "Mots": page_words})
            
            st.dataframe(page_stats, use_container_width=True, hide_index=True)

# Footer
st.divider()
st.info("🧠 **Insight PDF** • Powered by Mistral AI • Développé par Kandolo Herman (Chercheur en IA) • © 2024")
