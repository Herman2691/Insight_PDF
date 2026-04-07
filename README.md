# ✨ Insight PDF Pro

Analysez vos documents PDF avec l'intelligence artificielle — en quelques secondes.

---

## 📖 Description

**Insight PDF Pro** est une application web interactive construite avec **Streamlit** et propulsée par **Mistral AI**. Elle permet d'importer n'importe quel fichier PDF et d'en extraire la valeur en quelques clics : résumés, analyses sémantiques, conversations avec le document, lecture audio, génération de présentations PowerPoint automatiques et **évaluation de la qualité RAG**.

Le pipeline RAG (Retrieval-Augmented Generation) intègre plusieurs techniques avancées : semantic chunking, recherche hybride BM25 + embeddings, index vectoriel FAISS, reranking cross-encoder et cache persistant sur disque.

---

## 🚀 Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| 💬 **Chat intelligent** | Posez des questions en langage naturel sur le contenu de votre PDF |
| 📝 **Synthèse automatique** | Générez des résumés courts, moyens ou détaillés en un clic |
| 📊 **Analyse lexicale** | Statistiques de mots, fréquences, mots-clés et analyse sémantique des thèmes |
| 🔊 **Lecture audio** | Convertissez n'importe quelle page en fichier MP3 (multi-langues) |
| 🎯 **Présentation PowerPoint** | Générez un fichier `.pptx` structuré automatiquement par l'IA |
| 📐 **Évaluation RAG** | Mesurez la qualité de votre pipeline (Faithfulness, Answer Relevance, Context Recall) |
| ⬇️ **Export PDF** | Téléchargez l'historique de conversation en fichier PDF formaté |

---

## 🛠️ Stack technique

### Core
- **Frontend** : Streamlit
- **IA** : Mistral AI — modèle `mistral-large-latest`
- **Extraction PDF** : `pdfplumber` (recommandé) avec fallback automatique `PyPDF2`
- **Text-to-Speech** : `gTTS` (Google Text-to-Speech)
- **Génération PowerPoint** : `python-pptx`
- **Export PDF conversation** : `fpdf2`

### Pipeline RAG avancé
- **Embeddings** : `sentence-transformers` — modèle `all-MiniLM-L6-v2`
- **Index vectoriel** : `faiss-cpu` (avec fallback recherche linéaire)
- **Reranking** : `sentence-transformers` — modèle `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Évaluation RAG** : `ragas` + `datasets` (avec fallback LLM-as-judge)
- **Chunking** : Semantic chunking par paragraphes (avec fallback mécanique)
- **Recherche hybride** : BM25 + embeddings fusionnés via Reciprocal Rank Fusion (RRF)
- **Cache** : Embeddings persistants sur disque (MD5, format pickle)

---

## 📦 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-username/insight-pdf-pro.git
cd insight-pdf-pro
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer la clé API Mistral

Créez un fichier `.streamlit/secrets.toml` :

```toml
MISTRAL_API_KEY = "votre_clé_api_mistral"
```

Ou définissez la variable d'environnement :

```bash
export MISTRAL_API_KEY="votre_clé_api_mistral"
```

### 5. Lancer l'application

```bash
streamlit run app.py
```

---

## 📁 Structure du projet

```
insight-pdf-pro/
│
├── app.py                  # Application principale Streamlit
├── requirements.txt        # Dépendances Python
├── .embedding_cache/       # Cache persistant des embeddings (auto-généré)
├── .streamlit/
│   └── secrets.toml        # Clés API (à ne pas versionner)
└── README.md
```

---

## 📋 Dépendances (`requirements.txt`)

```
# Core
streamlit
mistralai
fpdf2

# Extraction PDF
pdfplumber
PyPDF2

# Audio
gTTS

# Présentation
python-pptx

# RAG — Embeddings & Reranking
sentence-transformers

# RAG — Index vectoriel (optionnel mais recommandé)
faiss-cpu

# RAG — Évaluation (optionnel)
ragas
datasets

# Analyse
numpy
pandas
```

> **Note :** `faiss-cpu`, `ragas` et `datasets` sont optionnels. L'application fonctionne sans eux avec des fallbacks automatiques.

---

## 💡 Utilisation

1. Importez votre fichier PDF via la **barre latérale gauche**
2. Attendez l'extraction, le chunking sémantique et l'encodage des embeddings (mis en cache automatiquement)
3. Naviguez entre les **6 onglets** selon votre besoin :

| Onglet | Usage |
|---|---|
| `💬 Chat` | Posez vos questions — le pipeline RAG hybride trouve les passages pertinents |
| `📝 Synthèse` | Choisissez le niveau de détail (Court / Moyen / Détaillé) et générez le résumé |
| `📊 Analyse` | Explorez les mots-clés et lancez l'analyse sémantique des thèmes |
| `🔊 Audio` | Sélectionnez une page et la langue, puis écoutez la lecture |
| `🎯 Présentation` | Configurez le nombre de slides et téléchargez le `.pptx` |
| `📐 Évaluation RAG` | Évaluez la qualité du pipeline sur une paire question/réponse |

### Paramètres RAG (barre latérale)

- **Chunks candidats (retrieval)** : nombre de chunks récupérés avant reranking (défaut : 10, recommandé : 8–12)
- **Chunks finaux (après reranking)** : nombre de chunks envoyés au LLM (défaut : 3, recommandé : 3–5)

---

## 🧠 Architecture RAG

```
PDF → pdfplumber / PyPDF2
    → Semantic Chunking (par paragraphes)
    → Encodage sentence-transformers (avec cache disque)
    → Index FAISS (persistant par fichier)

Question
    → BM25 (recherche lexicale)
    → Embeddings + FAISS (recherche sémantique)
    → Fusion RRF (Reciprocal Rank Fusion)
    → Cross-Encoder Reranking
    → Top-K chunks → Mistral AI → Réponse
```

### Stratégie selon la taille du document

| Taille du texte | Stratégie |
|---|---|
| ≤ 25 000 caractères | Envoi du texte complet au LLM (pas de RAG) |
| > 25 000 caractères | Pipeline RAG complet (retrieval → reranking → LLM) |

---

## 📐 Évaluation RAG

L'onglet **Évaluation RAG** mesure 3 métriques sur une paire question/réponse :

| Métrique | Description |
|---|---|
| **Faithfulness** | La réponse ne contient-elle que des informations issues du contexte ? |
| **Answer Relevance** | La réponse répond-elle précisément à la question posée ? |
| **Context Recall** | Le contexte récupéré contient-il les informations nécessaires ? |

**Méthode de calcul (par ordre de priorité) :**
1. **Vraie lib RAGAS** (`pip install ragas datasets`) — Faithfulness + Answer Relevancy via `ragas.evaluate()`
2. **LLM-as-judge** (fallback automatique) — les 3 métriques approchées via Mistral

---

## 🔒 Sécurité

- Ne partagez jamais votre fichier `secrets.toml` publiquement
- Ajoutez les entrées suivantes à votre `.gitignore` :

```gitignore
.streamlit/secrets.toml
.embedding_cache/
```

---

## 👤 Auteur

Développé par **Herman Kandolo**

---

## 📄 Licence

Ce projet est sous licence **MIT** — libre d'utilisation, de modification et de distribution.

---

## 🌐 Démo

Essayez l'application en ligne sans aucune installation :

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://votre-app.streamlit.app)
