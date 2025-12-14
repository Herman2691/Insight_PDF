Cette application Streamlit est un analyseur intelligent de documents PDF qui utilise l'API Mistral AI pour offrir plusieurs fonctionnalités d'analyse. Voici ce qu'elle fait :
Fonctionnalités principales
1. Questions/Réponses interactives L'application permet de poser des questions sur le contenu du PDF et obtient des réponses contextuelles via Mistral AI, avec références aux pages pertinentes.
2. Résumés automatiques Elle génère des résumés du document en trois niveaux : court (3-5 phrases), moyen (2-3 paragraphes), ou détaillé. Elle affiche aussi des statistiques (nombre de pages, mots, caractères).
3. Vérification orthographique et grammaticale L'application analyse chaque page pour détecter les erreurs d'orthographe et de grammaire, puis propose des corrections structurées.
4. Analyse lexicale et sémantique Elle effectue une analyse approfondie incluant :
•	Statistiques lexicales (vocabulaire unique, richesse lexicale)
•	Mots les plus fréquents
•	Analyse sémantique par IA (thèmes, ton, mots-clés, type de document, public cible)
•	Distribution du contenu par page
Fonctionnement technique
L'application extrait le texte du PDF page par page avec PyPDF2, stocke le contenu dans la session Streamlit, et utilise l'API Mistral AI pour toutes les analyses intelligentes. La clé API est chargée depuis un fichier .env pour la sécurité.
C'est essentiellement un assistant d'analyse documentaire complet qui combine extraction de données, traitement du langage naturel et interface utilisateur conviviale.

