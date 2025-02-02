import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from typing import Set, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime

# Import pour le modèle LSTM en utilisant PyTorch
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

# ----------------------------------------------------------------
# Configuration de la journalisation
# Créé par CAFAM pour le Hackathon HGEN IA 2025
# ----------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ----------------------------------------------------------------
# Constantes pour le scraping depuis data.gouv.fr
# ----------------------------------------------------------------
BASE_URL = "https://www.data.gouv.fr/fr/datasets/"
DOCUMENT_TYPES = [
    "DICRIM", "PCS", "PLU", "PPRN", "PCAET", "SCoT", "PLUi", "PICS", "DDRM", "SRADDET"
]

# ----------------------------------------------------------------
# Fonctions de téléchargement et de scraping
# ----------------------------------------------------------------

def download_file(url: str, output_folder: str, downloaded_files: Set[str], session: requests.Session) -> Optional[str]:
    """
    Télécharge un fichier à partir de l'URL et le sauvegarde dans output_folder.
    Vérifie si le fichier a déjà été téléchargé.
    """
    local_filename = os.path.join(output_folder, os.path.basename(url))
    if local_filename in downloaded_files:
        logger.info(f"Fichier déjà téléchargé : {local_filename}")
        return None
    try:
        with session.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        downloaded_files.add(local_filename)
        logger.info(f"Fichier téléchargé : {local_filename}")
        return local_filename
    except requests.RequestException as e:
        logger.error(f"Erreur lors du téléchargement de {url} : {e}")
        return None

def google_dorks(commune_name: str, file_types: List[str]) -> None:
    """
    Génère et affiche (dans les logs) des requêtes Google Dorks pour une recherche manuelle.
    """
    dork_templates = [
        "site:data.gouv.fr {commune} {doc_type} filetype:{filetype}",
        "site:georisques.gouv.fr {commune} {doc_type} filetype:{filetype}",
        "site:insee.fr {commune} {doc_type} filetype:{filetype}",
        "site:urbanisme.gouv.fr {commune} {doc_type} filetype:{filetype}",
        "site:geoportail-urbanisme.gouv.fr {commune} {doc_type} filetype:{filetype}"
    ]
    for file_type in file_types:
        for doc_type in DOCUMENT_TYPES:
            for template in dork_templates:
                dork_query = template.format(commune=commune_name, doc_type=doc_type, filetype=file_type)
                logger.info(f"Requête Google Dork : {dork_query}")

def process_dataset_page(full_link: str, file_types: List[str], commune_folder: str, downloaded_files: Set[str], session: requests.Session) -> List[str]:
    """
    Pour une page donnée de dataset, recherche et télécharge les fichiers correspondant aux types spécifiés.
    Retourne la liste des fichiers téléchargés pour cette page.
    """
    downloaded_summary = []
    try:
        dataset_page = session.get(full_link, timeout=10)
        dataset_page.raise_for_status()
        dataset_soup = BeautifulSoup(dataset_page.content, 'html.parser')
        for file_type in file_types:
            files = dataset_soup.find_all('a', href=True)
            for file in files:
                file_url = file['href']
                if file_url.lower().endswith(f".{file_type.lower()}"):
                    absolute_url = urljoin(BASE_URL, file_url)
                    result = download_file(absolute_url, commune_folder, downloaded_files, session)
                    if result:
                        downloaded_summary.append(result)
    except requests.RequestException as e:
        logger.error(f"Erreur lors de l'accès à {full_link} : {e}")
    return downloaded_summary

def find_and_download_files(commune_name: str, output_dir: str, file_types: List[str], max_workers: int = 10) -> List[str]:
    """
    Recherche des datasets pour la commune donnée, télécharge les fichiers correspondants et retourne un résumé des téléchargements.
    """
    commune_safe = "".join(c for c in commune_name if c.isalnum() or c in " -_").strip()
    commune_folder = os.path.join(output_dir, commune_safe)
    os.makedirs(commune_folder, exist_ok=True)
    downloaded_files: Set[str] = set(os.listdir(commune_folder))
    downloaded_summary: List[str] = []
    search_url = f"https://www.data.gouv.fr/fr/search/?q={commune_name}"
    session = requests.Session()
    try:
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if '/datasets/' in a['href']]
        unique_links = list(set(links))
        logger.info(f"Pour la commune '{commune_name}', trouvé {len(unique_links)} jeux de données.")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    process_dataset_page,
                    urljoin(BASE_URL, link),
                    file_types,
                    commune_folder,
                    downloaded_files,
                    session
                )
                for link in unique_links
            ]
            for future in as_completed(futures):
                downloaded_summary.extend(future.result())
        # Affichage des requêtes Google Dorks dans les logs
        google_dorks(commune_name, file_types)
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la recherche pour {commune_name} : {e}")
    summary_file = os.path.join(commune_folder, "download_summary.json")
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(downloaded_summary, f, indent=4, ensure_ascii=False)
        logger.info(f"Résumé des téléchargements généré : {summary_file}")
    except IOError as e:
        logger.error(f"Erreur lors de l'écriture du résumé {summary_file} : {e}")
    return downloaded_summary

# ----------------------------------------------------------------
# Fonctions de chargement de données pour le dashboard
# ----------------------------------------------------------------
@st.cache_data
def load_dashboard_data(uploaded_file):
    """
    Charge un fichier CSV ou JSON pour le dashboard, en convertissant la colonne 'date' en datetime.
    """
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, parse_dates=['date'])
        elif uploaded_file.name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        else:
            st.error("Format non supporté. Veuillez fournir un fichier CSV ou JSON.")
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier : {e}")
        return pd.DataFrame()

# ----------------------------------------------------------------
# Modèle LSTM avec PyTorch pour la prévision
# ----------------------------------------------------------------
class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=50, num_layers=1):
        """
        Modèle LSTM simple.
        Créé par CAFAM pour le Hackathon HGEN IA 2025.
        """
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

# ----------------------------------------------------------------
# Interface principale Streamlit
# ----------------------------------------------------------------
st.sidebar.title("Fonctionnalités")
mode = st.sidebar.radio("Sélectionnez le mode :", ("Collecte de données", "Dashboard & Prévision"))

if mode == "Collecte de données":
    st.title("Collecte de datasets depuis data.gouv.fr")
    st.markdown("""
    Lancez une collecte de datasets pour une ou plusieurs communes.
    Vous pouvez entrer une commune unique ou une liste de communes (séparées par des virgules).
    """)
    search_mode = st.radio("Mode de saisie :", ("Recherche par commune unique", "Ajouter une liste de communes"))
    if search_mode == "Recherche par commune unique":
        commune_input = st.text_input("Entrez le nom de la commune :", "Paris")
        communes = [commune_input.strip()] if commune_input.strip() != "" else []
    else:
        communes_input = st.text_area("Entrez les noms des communes (séparées par des virgules) :", "Paris, Lyon, Marseille")
        communes = [c.strip() for c in communes_input.split(",") if c.strip()]
    output_dir = st.text_input("Dossier de sortie :", value=r"E:\HGENIA")
    file_types_input = st.text_input("Extensions de fichiers à télécharger (séparées par des espaces) :", value="pdf json csv")
    file_types = [ft.strip() for ft in file_types_input.split()]
    max_workers = st.number_input("Nombre de threads (workers) :", min_value=1, max_value=50, value=10, step=1)
    if st.button("Lancer la collecte"):
        if not communes:
            st.error("Veuillez spécifier au moins une commune.")
        else:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            all_downloaded_files = {}
            total_communes = len(communes)
            for idx, commune in enumerate(communes, start=1):
                progress_text.text(f"Traitement de la commune : {commune} ({idx}/{total_communes})")
                st.write(f"### Traitement de la commune : {commune}")
                downloaded = find_and_download_files(commune, output_dir, file_types, max_workers)
                all_downloaded_files[commune] = downloaded
                st.write(f"Fichiers téléchargés pour {commune} :")
                st.json(downloaded)
                progress_bar.progress(int(idx / total_communes * 100))
            progress_text.text("Collecte terminée !")
            st.success("La collecte est terminée.")
            st.write("### Résumé global des fichiers téléchargés")
            st.json(all_downloaded_files)
            
elif mode == "Dashboard & Prévision":
    st.title("Dashboard et Prévision des Données")
    st.markdown("""
    Chargez un fichier CSV (contenant des données historiques, par exemple de 2000 à 2024) pour explorer diverses visualisations et effectuer une prévision sur 10 ans.
    """)
    uploaded_file = st.file_uploader("Choisissez un fichier CSV ou JSON", type=["csv", "json"])
    if uploaded_file is not None:
        df = load_dashboard_data(uploaded_file)
        if df.empty:
            st.warning("Le fichier est vide ou n'a pas pu être chargé.")
        else:
            st.subheader("Aperçu des données")
            st.dataframe(df.head(10))
            st.markdown("---")
            # Carte interactive
            if {'lat', 'lon'}.issubset(df.columns):
                st.subheader("Carte des communes")
                try:
                    st.map(df[['lat', 'lon']])
                except Exception as e:
                    st.error(f"Erreur lors de l'affichage de la carte : {e}")
            else:
                st.info("Les colonnes 'lat' et 'lon' ne sont pas présentes.")
            st.markdown("---")
            # Histogrammes interactifs
            st.subheader("Histogrammes")
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                selected_hist = st.selectbox("Sélectionnez une variable numérique pour l'histogramme :", numeric_cols, key="hist_dashboard")
                hist_chart = alt.Chart(df).mark_bar().encode(
                    alt.X(f"{selected_hist}:Q", bin=alt.Bin(maxbins=30), title=selected_hist),
                    alt.Y("count()", title="Nombre d'observations")
                ).properties(
                    width=600,
                    height=400,
                    title=f"Distribution de {selected_hist}"
                )
                st.altair_chart(hist_chart, use_container_width=True)
            else:
                st.info("Aucune variable numérique détectée.")
            st.markdown("---")
            # Diagramme en barres pour budgets
            st.subheader("Comparaison des Budgets")
            if 'commune' in df.columns:
                communes = df['commune'].tolist()
                selected_communes = st.multiselect("Sélectionnez les communes à comparer :", options=sorted(communes), default=communes[:5])
                if selected_communes:
                    df_filtered = df[df['commune'].isin(selected_communes)]
                    bar_data = df_filtered[['commune', 'budget_collectivite', 'budget_climatique']].melt(
                        id_vars='commune',
                        var_name='Type de budget',
                        value_name='Montant'
                    )
                    bar_chart = alt.Chart(bar_data).mark_bar().encode(
                        x=alt.X('commune:N', sort=None, title="Commune"),
                        y=alt.Y('Montant:Q', title="Montant (€)"),
                        color='Type de budget:N',
                        tooltip=['commune', 'Type de budget', 'Montant']
                    ).properties(
                        width=600,
                        height=400,
                        title="Budget collectif vs Budget climatique"
                    )
                    st.altair_chart(bar_chart, use_container_width=True)
            st.markdown("---")
            # Scatter plot
            st.subheader("Scatter Plot")
            scatter_cols = st.multiselect("Sélectionnez deux variables numériques pour le scatter plot :", numeric_cols, default=numeric_cols[:2])
            if len(scatter_cols) == 2:
                scatter_chart = alt.Chart(df).mark_circle(size=60).encode(
                    x=alt.X(f"{scatter_cols[0]}:Q", title=scatter_cols[0]),
                    y=alt.Y(f"{scatter_cols[1]}:Q", title=scatter_cols[1]),
                    tooltip=['commune'] + scatter_cols
                ).properties(
                    width=600,
                    height=400,
                    title=f"{scatter_cols[0]} vs {scatter_cols[1]}"
                )
                st.altair_chart(scatter_chart, use_container_width=True)
            else:
                st.info("Veuillez sélectionner exactement 2 variables numériques pour le scatter plot.")
            st.markdown("---")
            # Nuage de points multidimensionnel
            st.subheader("Nuage de points multidimensionnel")
            if set(['population', 'note_risques', 'taux_pollution_air']).issubset(df.columns):
                multi_chart = alt.Chart(df).mark_circle(size=80).encode(
                    x=alt.X('population:Q', title="Population"),
                    y=alt.Y('note_risques:Q', title="Note des risques"),
                    color=alt.Color('taux_pollution_air:Q', scale=alt.Scale(scheme='redyellowgreen'), title="Pollution de l'air"),
                    tooltip=['commune', 'population', 'note_risques', 'taux_pollution_air']
                ).properties(
                    width=600,
                    height=400,
                    title="Population vs Note des risques (couleur = Pollution)"
                )
                st.altair_chart(multi_chart, use_container_width=True)
            else:
                st.info("Les colonnes 'population', 'note_risques' et/ou 'taux_pollution_air' sont manquantes.")
            st.markdown("---")
            # Répartition des documents
            st.subheader("Répartition des documents disponibles")
            if 'documents' in df.columns:
                docs_series = df['documents'].dropna().apply(lambda x: [doc.strip() for doc in x.split(';')])
                all_docs = [doc for sublist in docs_series for doc in sublist]
                docs_count = pd.Series(all_docs).value_counts().reset_index()
                docs_count.columns = ['Document', 'Fréquence']
                pie_chart = alt.Chart(docs_count).mark_arc().encode(
                    theta=alt.Theta(field="Fréquence", type="quantitative"),
                    color=alt.Color(field="Document", type="nominal"),
                    tooltip=['Document', 'Fréquence']
                ).properties(
                    width=400,
                    height=400,
                    title="Distribution des types de documents"
                )
                st.altair_chart(pie_chart, use_container_width=True)
            else:
                st.info("La colonne 'documents' n'est pas présente.")
            st.markdown("---")
            # Autres visualisations via mapping
            st.subheader("Autres visualisations")
            additional_option = st.selectbox("Sélectionnez une visualisation :", 
                                               ["Budget collectif par commune", 
                                                "Nombre de catastrophes par commune", 
                                                "Taux de risque par commune",
                                                "Taux de pollution de l'air par commune",
                                                "Note des risques par commune"])
            mapping = {
                "Budget collectif par commune": "budget_collectivite",
                "Nombre de catastrophes par commune": "nombre_catastrophes",
                "Taux de risque par commune": "taux_risque",
                "Taux de pollution de l'air par commune": "taux_pollution_air",
                "Note des risques par commune": "note_risques"
            }
            selected_field = mapping.get(additional_option)
            if additional_option and 'commune' in df.columns and selected_field in df.columns:
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X('commune:N', sort='-y', title="Commune"),
                    y=alt.Y(f"{selected_field}:Q", title=additional_option),
                    tooltip=['commune', f"{selected_field}"]
                ).properties(
                    width=600,
                    height=400,
                    title=additional_option
                )
                st.altair_chart(chart, use_container_width=True)
            st.markdown("---")
            # Prévision LSTM avec PyTorch
            st.subheader("Prévision LSTM sur 10 ans (PyTorch)")
            st.markdown("""
            Cette section utilise un modèle LSTM implémenté avec **PyTorch** pour prévoir l’évolution d’une variable (par ex. budget collectif) sur les 10 prochaines années.
            Assurez-vous que le fichier contient une colonne **date** avec des enregistrements annuels.
            """)
            timeseries_var = st.selectbox("Sélectionnez la variable à prévoir :", numeric_cols, index=numeric_cols.index("budget_collectivite") if "budget_collectivite" in numeric_cols else 0)
            if st.button("Lancer la prévision LSTM"):
                if 'date' not in df.columns:
                    st.error("La colonne 'date' est nécessaire pour la prévision temporelle.")
                else:
                    # Prétraitement de la série temporelle
                    ts = df[['date', timeseries_var]].copy()
                    ts = ts.sort_values('date')
                    ts = ts.set_index('date')
                    ts = ts.resample('A').mean()  # On suppose des données annuelles
                    st.write("Aperçu de la série temporelle utilisée pour la prévision :")
                    st.dataframe(ts.tail(10))
                    
                    # Choix de la taille de la fenêtre (réduction si les données sont insuffisantes)
                    default_window_size = 3
                    if len(ts) < default_window_size + 1:
                        window_size = 1
                        st.warning(f"Pas assez de données pour une fenêtre de taille {default_window_size}. Utilisation d'une fenêtre de taille {window_size}.")
                    else:
                        window_size = default_window_size
                    
                    # Normalisation de la série temporelle
                    scaler = MinMaxScaler()
                    ts_scaled = scaler.fit_transform(ts)
                    
                    # Création des séquences pour l'entraînement (window_size = 3 par défaut)
                    X, y = [], []
                    for i in range(len(ts_scaled) - window_size):
                        X.append(ts_scaled[i:i+window_size])
                        y.append(ts_scaled[i+window_size])
                    X, y = np.array(X), np.array(y)
                    
                    if len(X) == 0:
                        st.error("Pas assez de données historiques pour la prévision.")
                    else:
                        # Conversion en tenseurs PyTorch
                        X_tensor = torch.tensor(X, dtype=torch.float32)
                        y_tensor = torch.tensor(y, dtype=torch.float32)
                        
                        # Définition et entraînement du modèle LSTM
                        model = LSTMModel(input_size=1, hidden_size=50, num_layers=1)
                        criterion = nn.MSELoss()
                        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
                        num_epochs = 200
                        st.info("Entraînement du modèle LSTM en cours...")
                        for epoch in range(num_epochs):
                            model.train()
                            optimizer.zero_grad()
                            outputs = model(X_tensor)
                            loss = criterion(outputs, y_tensor)
                            loss.backward()
                            optimizer.step()
                            if (epoch + 1) % 50 == 0:
                                st.write(f"Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.4f}")
                        st.success("Modèle entraîné avec succès!")
                        
                        # Prévision sur les 10 prochaines années
                        predictions = []
                        last_sequence = ts_scaled[-window_size:]
                        current_seq = last_sequence.copy()
                        model.eval()
                        with torch.no_grad():
                            for _ in range(10):
                                seq_tensor = torch.tensor(current_seq.reshape(1, window_size, 1), dtype=torch.float32)
                                pred = model(seq_tensor)
                                pred_value = pred.item()
                                predictions.append(pred_value)
                                current_seq = np.append(current_seq[1:], [[pred_value]], axis=0)
                        
                        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1,1))
                        forecast_years = pd.date_range(start=ts.index[-1] + pd.offsets.DateOffset(years=1), periods=10, freq='A')
                        forecast_df = pd.DataFrame({timeseries_var: predictions.flatten()}, index=forecast_years)
                        
                        st.subheader("Prévisions des Recettes sur 10 ans")
                        st.line_chart(forecast_df)
                        st.write(forecast_df)
    else:
        st.info("Veuillez charger un fichier pour afficher le dashboard.")
