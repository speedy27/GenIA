import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import requests
import folium
from streamlit_folium import folium_static
import boto3
from io import StringIO, BytesIO
import datetime
import plotly.express as px

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Analyse des Risques Climatiques, Environnementaux et Financiers", 
    layout="wide"
)

# Titre principal
st.title("Analyse des Risques Climatiques, Environnementaux et Financiers")

#############################################
# Fonctions de chargement des données
#############################################

@st.cache_data
def load_data_local(file_path: str) -> pd.DataFrame:
    """
    Charge les données depuis un fichier CSV local.
    Essaye d'abord l'encodage 'latin1', puis 'ISO-8859-1' en cas d'erreur.
    """
    try:
        df = pd.read_csv(file_path, encoding='latin1', sep=';')
    except Exception as e:
        st.warning("Erreur avec l'encodage 'latin1', tentative avec 'ISO-8859-1'")
        df = pd.read_csv(file_path, encoding='ISO-8859-1', sep=';')
    return df

@st.cache_data
def load_data_from_s3(bucket_name: str, key: str, aws_access_key_id: str, aws_secret_access_key: str) -> pd.DataFrame:
    """
    Charge les données depuis un bucket Amazon S3.
    Paramètres :
      - bucket_name: nom du bucket S3
      - key: chemin du fichier dans le bucket
      - aws_access_key_id et aws_secret_access_key: vos identifiants AWS
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        # Lire le contenu en mémoire et le convertir en DataFrame
        data = response['Body'].read()
        # On essaie d'abord avec 'latin1'
        try:
            df = pd.read_csv(StringIO(data.decode('latin1')), sep=';')
        except Exception as e:
            df = pd.read_csv(StringIO(data.decode('ISO-8859-1')), sep=';')
        return df
    except Exception as e:
        st.error(f"Erreur lors de la récupération du fichier S3 : {e}")
        return pd.DataFrame()  # retourne un DataFrame vide en cas d'erreur

#############################################
# Choix de la source des données
#############################################

st.sidebar.header("Source des Données")
source_option = st.sidebar.radio(
    "Choisissez la source des données :",
    ("Fichier Local", "Amazon S3")
)

if source_option == "Fichier Local":
    file_path = st.sidebar.text_input("Chemin du fichier CSV local", value="Data_Completed.csv")
    df = load_data_local(file_path)
else:
    st.sidebar.subheader("Paramètres S3")
    bucket_name = st.sidebar.text_input("Nom du Bucket S3", value="votre-bucket")
    key = st.sidebar.text_input("Chemin du fichier dans le bucket", value="Data_Completed.csv")
    # Il est recommandé de stocker ces clés dans st.secrets pour plus de sécurité
    aws_access_key_id = st.sidebar.text_input("AWS Access Key ID", type="password", value=st.secrets.get("aws_access_key_id", ""))
    aws_secret_access_key = st.sidebar.text_input("AWS Secret Access Key", type="password", value=st.secrets.get("aws_secret_access_key", ""))
    
    if aws_access_key_id and aws_secret_access_key and bucket_name and key:
        df = load_data_from_s3(bucket_name, key, aws_access_key_id, aws_secret_access_key)
    else:
        st.error("Veuillez renseigner tous les paramètres S3.")
        st.stop()

#############################################
# Prétraitement des données
#############################################

# Vérifier la présence des colonnes indispensables
required_columns = ['dat_publi_dicrim', 'nom_region', 'nom_departement', 'nom_commune', 'lat', 'lon']
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error(f"Les colonnes suivantes sont manquantes dans le CSV: {', '.join(missing_columns)}")
    st.stop()

# Conversion de la date et extraction de l'année
df['dat_publi_dicrim'] = pd.to_datetime(df['dat_publi_dicrim'], errors='coerce')
df['année'] = df['dat_publi_dicrim'].dt.year

# Simulation des données financières (à remplacer par des données réelles ou des appels API)
np.random.seed(42)
df['budget_alloué'] = np.random.randint(100000, 5000000, size=len(df))
df['dépenses_risque'] = np.random.randint(50000, 2000000, size=len(df))

#############################################
# Sidebar : Filtres et options supplémentaires
#############################################

st.sidebar.header("Filtres et Options")

# Sélection de l'intervalle d'années
min_year = int(df['année'].min())
max_year = int(df['année'].max())
selected_years = st.sidebar.slider(
    "Sélectionnez l'intervalle d'années", 
    min_year, max_year, (min_year, max_year), step=1
)
df = df[(df['année'] >= selected_years[0]) & (df['année'] <= selected_years[1])]

# Option d'afficher les données brutes
if st.sidebar.checkbox("Afficher les données brutes"):
    st.subheader("Données brutes")
    st.dataframe(df)

# Option de téléchargement des données filtrées
csv = df.to_csv(index=False, sep=';').encode('utf-8')
st.sidebar.download_button(
    label="Télécharger les données filtrées",
    data=csv,
    file_name='data_filtrée.csv',
    mime='text/csv',
)

# Information sur les sources
st.sidebar.info("Sources de données : API Géorisques, Drias, ADEME, OpenWeatherMap, Data.gouv, Amazon S3")

#############################################
# Organisation en onglets (tabs)
#############################################

tabs = st.tabs([
    "Comparaison", 
    "Carte Interactive", 
    "Visualisations", 
    "Météo", 
    "API Data.gouv"
])

#############################################
# Onglet 1 : Comparaison entre Entités
#############################################
with tabs[0]:
    st.header("Comparaison entre Entités")
    compare_type = st.radio(
        "Choisissez le type de comparaison:",
        ('Régions', 'Départements', 'Communes'),
        index=0,
    )

    if compare_type == 'Régions':
        entities = df['nom_region'].dropna().unique()
        col1, col2 = st.columns(2)
        with col1:
            entity1 = st.selectbox("Région 1", options=sorted(entities))
        with col2:
            entity2 = st.selectbox("Région 2", options=sorted(entities))
        
        df1 = df[df['nom_region'] == entity1]
        df2 = df[df['nom_region'] == entity2]
        st.subheader(f"Comparaison entre {entity1} et {entity2}")

        st.write("Aperçu de la Région 1:")
        st.dataframe(df1.head())
        st.write("Aperçu de la Région 2:")
        st.dataframe(df2.head())

        # Graphique de comparaison des budgets alloués par année
        fig, ax = plt.subplots(figsize=(10, 5))
        df1.groupby('année')['budget_alloué'].sum().plot(label=entity1, marker='o', ax=ax)
        df2.groupby('année')['budget_alloué'].sum().plot(label=entity2, marker='o', ax=ax)
        ax.set_title("Comparaison des Budgets Alloués par Année")
        ax.set_xlabel("Année")
        ax.set_ylabel("Budget Alloué (€)")
        ax.legend()
        st.pyplot(fig)

    elif compare_type == 'Départements':
        entities = df['nom_departement'].dropna().unique()
        col1, col2 = st.columns(2)
        with col1:
            entity1 = st.selectbox("Département 1", options=sorted(entities))
        with col2:
            entity2 = st.selectbox("Département 2", options=sorted(entities))
        
        df1 = df[df['nom_departement'] == entity1]
        df2 = df[df['nom_departement'] == entity2]
        st.subheader(f"Comparaison entre {entity1} et {entity2}")

        st.write("Aperçu du Département 1:")
        st.dataframe(df1.head())
        st.write("Aperçu du Département 2:")
        st.dataframe(df2.head())

        # Graphique de comparaison des dépenses de risque par année
        fig, ax = plt.subplots(figsize=(10, 5))
        df1.groupby('année')['dépenses_risque'].sum().plot(label=entity1, marker='o', ax=ax)
        df2.groupby('année')['dépenses_risque'].sum().plot(label=entity2, marker='o', ax=ax)
        ax.set_title("Comparaison des Dépenses de Risque par Année")
        ax.set_xlabel("Année")
        ax.set_ylabel("Dépenses de Risque (€)")
        ax.legend()
        st.pyplot(fig)

    elif compare_type == 'Communes':
        entities = df['nom_commune'].dropna().unique()
        col1, col2 = st.columns(2)
        with col1:
            entity1 = st.selectbox("Commune 1", options=sorted(entities))
        with col2:
            entity2 = st.selectbox("Commune 2", options=sorted(entities))
        
        df1 = df[df['nom_commune'] == entity1]
        df2 = df[df['nom_commune'] == entity2]
        st.subheader(f"Comparaison entre {entity1} et {entity2}")

        st.write("Aperçu de la Commune 1:")
        st.dataframe(df1.head())
        st.write("Aperçu de la Commune 2:")
        st.dataframe(df2.head())

        # Graphique de comparaison des budgets alloués par année
        fig, ax = plt.subplots(figsize=(10, 5))
        df1.groupby('année')['budget_alloué'].sum().plot(label=entity1, marker='o', ax=ax)
        df2.groupby('année')['budget_alloué'].sum().plot(label=entity2, marker='o', ax=ax)
        ax.set_title("Comparaison des Budgets Alloués par Année")
        ax.set_xlabel("Année")
        ax.set_ylabel("Budget Alloué (€)")
        ax.legend()
        st.pyplot(fig)

#############################################
# Onglet 2 : Carte Interactive avec Folium
#############################################
with tabs[1]:
    st.header("Carte Interactive")
    # Création d'une carte centrée sur la France
    m = folium.Map(location=[46.603354, 1.8883335], zoom_start=6)
    
    # Optionnel : Filtrer par type d'entité pour l'affichage des marqueurs
    entity_filter = st.selectbox("Filtrer par :", ["Toutes", "Région", "Département", "Commune"])
    
    # Ajout de marqueurs pour chaque enregistrement
    for idx, row in df.iterrows():
        popup_text = f"""
        <b>Date de publication :</b> {row['dat_publi_dicrim'].date()}<br>
        <b>Région :</b> {row['nom_region']}<br>
        <b>Département :</b> {row['nom_departement']}<br>
        <b>Commune :</b> {row['nom_commune']}<br>
        <b>Budget Alloué :</b> {row['budget_alloué']} €<br>
        <b>Dépenses de Risque :</b> {row['dépenses_risque']} €
        """
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=popup_text,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
    
    folium_static(m, width=800, height=600)

#############################################
# Onglet 3 : Visualisations Complémentaires
#############################################
with tabs[2]:
    st.header("Visualisations Complémentaires")
    
    # Histogramme des budgets alloués
    st.subheader("Distribution des Budgets Alloués")
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.histplot(df['budget_alloué'], bins=20, kde=True, ax=ax1, color="skyblue")
    ax1.set_xlabel("Budget Alloué (€)")
    ax1.set_title("Histogramme des Budgets Alloués")
    st.pyplot(fig1)
    
    # Graphique interactif Plotly des dépenses de risque par année
    st.subheader("Dépenses de Risque par Année (Plotly)")
    df_grouped = df.groupby('année')['dépenses_risque'].sum().reset_index()
    fig2 = px.bar(
        df_grouped, 
        x='année', 
        y='dépenses_risque', 
        text='dépenses_risque', 
        title="Dépenses de Risque par Année"
    )
    st.plotly_chart(fig2, use_container_width=True)

#############################################
# Onglet 4 : Informations Météo via OpenWeatherMap
#############################################
with tabs[3]:
    st.header("Informations Météo")
    st.write("Récupération des informations météo via l'API OpenWeatherMap.")
    
    # Saisie de la clé API (idéalement à stocker dans st.secrets)
    api_key = st.text_input("Entrez votre clé API OpenWeatherMap", type="password")
    if api_key:
        city = st.text_input("Entrez le nom de la ville", "Paris")
        
        def get_weather(city, api_key):
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=fr"
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                st.error(f"Erreur lors de la récupération de la météo : {e}")
                return None
        
        weather_data = get_weather(city, api_key)
        if weather_data:
            st.subheader(f"Météo actuelle à {city}")
            st.write(f"**Température :** {weather_data['main']['temp']} °C")
            st.write(f"**Ressenti :** {weather_data['main']['feels_like']} °C")
            st.write(f"**Conditions :** {weather_data['weather'][0]['description']}")
            st.write(f"**Humidité :** {weather_data['main']['humidity']} %")
            st.write(f"**Vitesse du vent :** {weather_data['wind']['speed']} m/s")
        else:
            st.warning("Aucune donnée météo disponible.")
    else:
        st.info("Veuillez entrer votre clé API pour afficher la météo.")

#############################################
# Onglet 5 : API Data.gouv - Jeux de Données Open Data
#############################################
with tabs[4]:
    st.header("Jeux de Données Data.gouv.fr")
    st.write("Exemple de récupération de jeux de données depuis l'API Data.gouv.fr.")
    
    def get_datasets():
        url = "https://www.data.gouv.fr/api/1/datasets/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Erreur lors de la récupération des datasets : {e}")
            return None

    datasets = get_datasets()
    if datasets:
        st.subheader("Liste des premiers jeux de données")
        for ds in datasets.get('data', [])[:5]:
            st.markdown(f"**{ds.get('title')}**")
            st.write(ds.get('description'))
            st.write(f"[En savoir plus]({ds.get('uri')})")
    else:
        st.warning("Aucun dataset trouvé.")
