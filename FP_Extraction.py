# -*- coding: utf-8 -*- 
"""
Created on Wed Jan 29 20:36:23 2025

@author: flori
"""

import pandas as pd
import requests

# Définition des types de risques naturels et technologiques
RISQUES_NATURELS = ["inondation", "séisme", "mouvementTerrain", "retraitGonflementArgile", "radon"]
RISQUES_TECHNOLOGIQUES = ["icpe", "nucleaire", "canalisationsMatieresDangereuses", "pollutionSols"]

# Liste des risques climatiques potentiels
RISQUES_CLIMATIQUES = [
    "inondation", "feu de forêt", "tempête", "sécheresse", "vague de chaleur",
    "érosion du littoral", "élévation du niveau de la mer", "retrait-gonflement des argiles",
    "pollution de l'air", "stress hydrique", "perte de biodiversité"
]

# Liste des actions d'adaptation possibles
ACTIONS_ADAPTATION = [
    "mise en place de digues", "reboisement", "zones tampons",
    "gestion des eaux pluviales", "aménagement du territoire",
    "réduction des émissions de gaz à effet de serre", "renforcement des infrastructures",
    "systèmes d’alerte précoce", "éducation et sensibilisation"
]

# Extraction des codes INSEE des communes (limité à 10)
def extract_com_column(file_path, limit=50):
    try:
        df = pd.read_csv(file_path, dtype={"COM": str})  
        if "COM" in df.columns:
            return df["COM"].dropna().tolist()[:limit]  # Récupérer seulement 10 communes
        else:
            print("⚠ La colonne 'COM' est absente du fichier.")
            return []
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier : {e}")
        return []

# Récupération des coordonnées géographiques (latitude, longitude) pour un code INSEE
def fetch_coordinates(code_insee):
    url = f"https://geo.api.gouv.fr/communes/{code_insee}?fields=centre"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "centre" in data and "coordinates" in data["centre"]:
                lon, lat = map(float, data["centre"]["coordinates"])  # Conversion explicite en float
                return lat, lon
    except Exception as e:
        print(f"⚠ Erreur API pour {code_insee}: {e}")
    return None, None

# Récupération de la zone de sismicité en fonction des coordonnées
def fetch_sismicite(lat, lon):
    url = f"https://georisques.gouv.fr/api/v1/zonage_sismique?latlon={lon},{lat}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]["zone_sismicite"]
    except Exception as e:
        print(f"⚠ Erreur API sismicité pour ({lat}, {lon}): {e}")
    return "Non disponible"

# Récupération des données de retrait-gonflement des argiles (RGA) en fonction des coordonnées
def fetch_rga(lat, lon):
    url = f"https://georisques.gouv.fr/api/v1/rga?latlon={lon},{lat}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("exposition", "Non disponible"), data.get("codeExposition", "Non disponible")
    except Exception as e:
        print(f"⚠ Erreur API RGA pour ({lat}, {lon}): {e}")
    return "Non disponible", "Non disponible"

# Récupération des risques et adaptation par commune
def fetch_risk_reports(com_codes, output_file):
    base_url = "https://www.georisques.gouv.fr/api/v1/resultats_rapport_risque?code_insee="
    data_list = []

    for code in com_codes:
        lat, lon = fetch_coordinates(code)
        sismicite = fetch_sismicite(lat, lon) if lat and lon else "Non disponible"
        rga_expo, rga_code = fetch_rga(lat, lon) if lat and lon else ("Non disponible", "Non disponible")

        response = requests.get(base_url + str(code))
        
        if response.status_code == 200:
            print(f"✅ Réponse 200 pour INSEE {code}")
            json_data = response.json()
            
            commune = json_data.get("commune", {})
            risques_naturels = json_data.get("risquesNaturels", {})
            risques_technologiques = json_data.get("risquesTechnologiques", {})

            # Initialisation des colonnes risques à False
            data = {
                "Code INSEE": commune.get("codeInsee", code),
                "Commune": commune.get("libelle", "Inconnu"),
                "Code Postal": commune.get("codePostal", "Inconnu"),
                "URL Rapport": json_data.get("url", "Non disponible"),
                "Latitude": float(lat) if lat else "Non disponible",  # Assurez-vous que la latitude soit en float
                "Longitude": float(lon) if lon else "Non disponible",  # Assurez-vous que la longitude soit en float
                "Zone Sismicité": sismicite,
                "RGA Exposition": rga_expo,
                "RGA Code": rga_code
            }

            # Ajout des colonnes pour chaque type de risque avec True/False
            for risque in RISQUES_NATURELS:
                data[risque] = risques_naturels.get(risque, {}).get("present", False)
            
            for risque in RISQUES_TECHNOLOGIQUES:
                data[risque] = risques_technologiques.get(risque, {}).get("present", False)

            # Déduire les risques climatiques potentiels
            risques_identifiés = [r for r in RISQUES_NATURELS + RISQUES_TECHNOLOGIQUES if data[r]]
            risques_climatiques_retenus = [r for r in RISQUES_CLIMATIQUES if r.lower() in " ".join(risques_identifiés).lower()]

            # Ajout des colonnes risques climatiques avec True/False
            for risque_climatique in RISQUES_CLIMATIQUES:
                data[risque_climatique] = risque_climatique in risques_climatiques_retenus

            # Définition des actions d'adaptation en fonction des risques détectés
            actions_retenues = ACTIONS_ADAPTATION[:3] if risques_identifiés else []  # Limité à 3 actions

            # Ajout des colonnes actions d’adaptation avec True/False
            for action in ACTIONS_ADAPTATION:
                data[action] = action in actions_retenues

            data_list.append(data)

        else:
            print(f"❌ Erreur {response.status_code} pour le code {code}")

    # Création et enregistrement du DataFrame
    df_output = pd.DataFrame(data_list)
    df_output.to_csv(output_file, index=False, encoding='utf-8')

    # Affichage d'un aperçu des données
    print(f"📂 Données enregistrées dans {output_file}")
    print("\n🔍 Aperçu des 5 premières lignes :")
    print(df_output.head())

# --- Utilisation du script ---
file_path = "v_commune_2024.csv"  # Remplacez par le chemin de votre fichier CSV
output_file = "resultats_risques_10_villes.csv"

com_column = extract_com_column(file_path, limit=50)  # Limité à 10 communes
if com_column:
    fetch_risk_reports(com_column, output_file)
