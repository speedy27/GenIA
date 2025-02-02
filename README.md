# GenIA
Développement d’un portail interactif intégrant un agent IA basé sur Amazon Bedrock pour analyser les risques climatiques et environnementaux. Il combine chatbot RAG, base vectorielle (Titan Embeddings, ChromaDB), carte interactive et simulateur de coûts. L’IA utilise AWS Lambda, OpenSearch, OpenAPI pour automatiser les analyses et recommandations

# GenIA

GenIA est un portail interactif dédié à l’analyse des risques climatiques et environnementaux, développé dans le cadre du Hackathon HGEN IA 2025 par CAFAM. Le projet intègre plusieurs modules complémentaires :

- **Collecte de données**  
  Récupération automatisée de datasets depuis data.gouv.fr via des scripts de scraping, incluant des requêtes Google Dorks pour affiner les recherches manuelles.
  
- **Dashboard interactif**  
  Interface utilisateur développée avec Streamlit qui permet de visualiser et explorer les données collectées à l’aide de cartes interactives, histogrammes, diagrammes en barres, scatter plots et autres graphiques (générés avec Altair).
  
- **Prévision temporelle**  
  Implémentation d’un modèle LSTM en PyTorch pour prévoir l’évolution d’une variable (ex. le budget collectif) sur les 10 prochaines années, avec un prétraitement des séries temporelles et une normalisation (via Scikit-Learn).

> **Note :** La fonctionnalité de simulateur de coûts, initialement prévue, n’est pas intégrée dans cette version du projet.

---

## Table des Matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture du Projet](#architecture-du-projet)
- [Technologies Utilisées](#technologies-utilisées)
- [Installation](#installation)
  - [Prérequis](#prérequis)
  - [Clonage du Dépôt et Installation des Dépendances](#clonage-du-dépôt-et-installation-des-dépendances)
  - [Exécution de l’Application](#exécution-de-lapplication)
- [Utilisation](#utilisation)
  - [Collecte de Données](#collecte-de-données)
  - [Dashboard & Prévision](#dashboard--prévision)
- [Contribution](#contribution)
- [Licence](#licence)
- [Contact](#contact)

---

## Fonctionnalités

### Collecte de données automatisée

Recherche et téléchargement de datasets relatifs aux communes ciblées depuis data.gouv.fr. Les fonctions de scraping exploitent des connexions parallèles pour optimiser le traitement, et génèrent des requêtes Google Dorks afin d’aiguiller d’éventuelles recherches manuelles.

### Dashboard interactif

Visualisation des données collectées via une interface Streamlit, avec support pour :

- **Cartes interactives** (affichage des localisations via latitude/longitude)
- **Histogrammes et diagrammes en barres** pour explorer des variables numériques
- **Scatter plots et nuages de points multidimensionnels**
- **Répartition des types de documents** disponibles (via diagramme en secteurs)

### Prévision temporelle avec LSTM

Un modèle LSTM (implémenté en PyTorch) est utilisé pour effectuer des prévisions sur une variable choisie (par exemple, le budget collectif) sur 10 ans. Le processus inclut la normalisation des données, la création de séquences temporelles et l’entraînement supervisé du modèle.

---

## Architecture du Projet

Le projet se divise en deux modules principaux :

### Module de Collecte de Données

- **Scraping**  
  Récupère automatiquement les pages de datasets sur data.gouv.fr et télécharge les fichiers aux formats spécifiés (pdf, json, csv, etc.).
  
- **Gestion des Fichiers**  
  Vérifie et conserve un historique des fichiers déjà téléchargés afin d’éviter les doublons.
  
- **Google Dorks**  
  Génère des requêtes pour faciliter des recherches complémentaires en ligne.

### Module Dashboard & Prévision

- **Dashboard**  
  Interface Streamlit pour l’exploration des données collectées à l’aide de visualisations interactives.
  
- **Prévision**  
  Prétraitement des séries temporelles et utilisation d’un modèle LSTM pour prévoir l’évolution d’une variable sur une décennie.

---

## Technologies Utilisées

### Python

Langage principal du projet pour le développement des scripts de scraping, du dashboard et du modèle de prévision.

### Libraries et Frameworks

- **Requests & BeautifulSoup** : Pour le scraping et le téléchargement des données.
- **Streamlit** : Pour la création de l’interface interactive du dashboard.
- **Pandas, Numpy** : Pour la manipulation et l’analyse des données.
- **Altair** : Pour la génération de visualisations interactives.
- **PyTorch & Scikit-Learn** : Pour la mise en place et l’entraînement du modèle LSTM.
- **Concurrent.futures** : Pour la gestion de l’exécution parallèle lors du scraping.

---

## Installation

### Prérequis

- Python 3.8 ou supérieur
- pip
- Accès Internet pour le téléchargement des datasets
- *(Optionnel)* Environnement virtuel (virtualenv, conda, etc.)

### Clonage du Dépôt et Installation des Dépendances

#### Cloner le dépôt Git :

```bash
git clone https://github.com/votre-organisation/genia.git
cd genia
