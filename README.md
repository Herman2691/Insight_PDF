# ✨ Insight PDF Pro

> **Analysez vos documents PDF avec l'intelligence artificielle — en quelques secondes.**

---

## 📖 Description

**Insight PDF Pro** est une application web interactive construite avec **Streamlit** et propulsée par **Mistral AI**. Elle permet d'importer n'importe quel fichier PDF et d'en extraire la valeur en quelques clics : résumés, analyses sémantiques, conversations avec le document, lecture audio et génération de présentations PowerPoint automatiques.

---

## 🚀 Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| 💬 **Chat intelligent** | Posez des questions en langage naturel sur le contenu de votre PDF |
| 📝 **Synthèse automatique** | Générez des résumés courts, moyens ou détaillés en un clic |
| 📊 **Analyse lexicale** | Statistiques de mots, fréquences, mots-clés et analyse sémantique des thèmes |
| 🔊 **Lecture audio** | Convertissez n'importe quelle page en fichier MP3 (français & anglais) |
| 🎯 **Présentation PowerPoint** | Générez un fichier `.pptx` structuré automatiquement par l'IA |

---

## 🛠️ Stack technique

- **Frontend** : [Streamlit](https://streamlit.io/)
- **IA** : [Mistral AI](https://mistral.ai/) — modèle `mistral-large-latest`
- **Extraction PDF** : `PyPDF2`
- **Text-to-Speech** : `gTTS` (Google Text-to-Speech)
- **Génération PowerPoint** : `python-pptx`
- **Analyse de texte** : `re`, `collections.Counter`

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
├── .streamlit/
│   └── secrets.toml        # Clés API (à ne pas versionner)
└── README.md
```

---

## 📋 Dépendances (`requirements.txt`)

```
streamlit
mistralai
PyPDF2
gTTS
python-pptx
```

---

## 💡 Utilisation

1. **Importez** votre fichier PDF via la barre latérale gauche
2. **Attendez** l'extraction automatique du texte
3. **Naviguez** entre les 5 onglets selon votre besoin :
   - `💬 Chat` → posez vos questions
   - `📝 Synthèse` → choisissez le niveau de détail et générez le résumé
   - `📊 Analyse` → explorez les mots-clés et lancez l'analyse sémantique
   - `🔊 Audio` → sélectionnez une page et la langue, puis écoutez
   - `🎯 Présentation` → configurez le nombre de slides et téléchargez le `.pptx`

---

## 🔒 Sécurité

- Ne partagez **jamais** votre fichier `secrets.toml` publiquement
- Ajoutez `.streamlit/secrets.toml` à votre `.gitignore`

```gitignore
.streamlit/secrets.toml
```

---

## 👤 Auteur

Développé par **Herman Kandolo**

---

## 📄 Licence

Ce projet est sous licence **MIT** — libre d'utilisation, de modification et de distribution.

---

## 🌐 Démo

> Essayez l'application en ligne sans aucune installation :

### 👉 [https://lecteurintelligentpdf-ma48ujfhtuhxqprgjjkhqq.streamlit.app/](https://lecteurintelligentpdf-ma48ujfhtuhxqprgjjkhqq.streamlit.app/)
