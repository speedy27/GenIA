# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 20:44:09 2025

@author: flori
"""

# -*- coding: utf-8 -*-
"""
Script complet (APIs réelles) :
 1) Lit un CSV local (codes INSEE)
 2) Récupère : 
    - Coordonnées (geo.api.gouv.fr)
    - GeoRisques (rapport_risque, sismicité, RGA, DICRIM, radon)
    - PCAET (data.ademe.fr)
    - Bornes IRVE (opendata.reseaux-energies.fr)
    - Eligibilité réseau de chaleur/froid (France Chaleur Urbaine)
 3) Classifie 3 risques SFIL (inondation, séisme, retraitGonflementArgile) 
    et évalue l'adaptation (présence d'un DICRIM ou d'un PCAET)
 4) Exporte le tout dans un CSV (Latitude/Longitude en float)
 5) Crée une carte Folium interactive 
"""

import requests
import pandas as pd
import folium
from tqdm import tqdm

# -------------------------------------------------------------------------
# 1) LISTES DE RISQUES "SFIL" (réels, selon l'API GeoRisques)
# -------------------------------------------------------------------------
PHYSICAL_ACUTE_RISKS = [
    "inondation",  # 'inondation' dans GeoRisques
    "séisme"       # 'séisme' dans GeoRisques
]
PHYSICAL_CHRONIC_RISKS = [
    "retraitGonflementArgile"  # 'retraitGonflementArgile' dans GeoRisques
]
ENVIRONMENTAL_RISKS = []
ALL_SFIL_RISKS = PHYSICAL_ACUTE_RISKS + PHYSICAL_CHRONIC_RISKS + ENVIRONMENTAL_RISKS

# GeoRisques renvoie aussi "mouvementTerrain", "radon", "pollutionSols", etc. 
# Ici, on se concentre sur 3 risques SFIL.

# -------------------------------------------------------------------------
# 2) LECTURE CSV (Codes INSEE)
# -------------------------------------------------------------------------
def extract_com_column(file_path, limit=None):
    """
    Lit un fichier CSV local contenant une colonne 'COM' (codes INSEE).
    """
    try:
        df = pd.read_csv(file_path, dtype={"COM": str})
        if "COM" not in df.columns:
            print("⚠ La colonne 'COM' est absente du fichier.")
            return []
        codes = df["COM"].dropna().tolist()
        if limit is not None:
            codes = codes[:limit]
        return codes
    except Exception as e:
        print(f"❌ Erreur lecture du fichier CSV : {e}")
        return []

# -------------------------------------------------------------------------
# 3) APIS REELLES (GeoRisques, ADEME, IRVE, Chaleur Urbaine)
# -------------------------------------------------------------------------

### 3.1 : GEOLOCALISATION VIA geo.api.gouv.fr
def fetch_coordinates(code_insee):
    """
    https://geo.api.gouv.fr/communes/{code_insee}?fields=centre
    Retourne (latitude, longitude) en float, ou (None, None) si échec.
    """
    url = f"https://geo.api.gouv.fr/communes/{code_insee}?fields=centre"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "centre" in data and "coordinates" in data["centre"]:
                lon, lat = map(float, data["centre"]["coordinates"])
                return float(lat), float(lon)
    except Exception as e:
        print(f"⚠ Erreur geo.api.gouv.fr pour {code_insee} : {e}")
    return None, None

### 3.2 : RAPPORT RISQUE & AUTRES (GeoRisques)
def fetch_resultats_rapport_risque(code_insee):
    """
    https://www.georisques.gouv.fr/api/v1/resultats_rapport_risque?code_insee={code_insee}
    Renvoie un JSON décrivant 'risquesNaturels' et 'risquesTechnologiques', etc.
    """
    url = f"https://www.georisques.gouv.fr/api/v1/resultats_rapport_risque?code_insee={code_insee}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"⚠ Erreur rapport_risque GeoRisques : {e}")
    return {}

def fetch_dicrim(code_insee):
    """
    DICRIM : https://georisques.gouv.fr/api/v1/gaspar/dicrim?code_insee={code_insee}
    Renvoie True si un DICRIM est disponible
    """
    url = f"https://georisques.gouv.fr/api/v1/gaspar/dicrim?code_insee={code_insee}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("total", 0) > 0
    except Exception as e:
        print(f"⚠ Erreur DICRIM pour {code_insee}: {e}")
    return False

def fetch_radon(code_insee):
    """
    Potentiel radon : https://georisques.gouv.fr/api/v1/radon?code_insee={code_insee}
    Renvoie un code '1', '2', ou '3' (ou 'Non disponible').
    """
    url = f"https://georisques.gouv.fr/api/v1/radon?code_insee={code_insee}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("potentielRadon", "Non disponible")
    except Exception as e:
        print(f"⚠ Erreur Radon pour {code_insee}: {e}")
    return "Non disponible"

def fetch_sismicite(lat, lon):
    """
    https://georisques.gouv.fr/api/v1/zonage_sismique?latlon={lon},{lat}
    Renvoie un code de zone sismique (1 à 5) ou 'Non disponible'.
    """
    if lat is None or lon is None:
        return "Non disponible"
    url = f"https://georisques.gouv.fr/api/v1/zonage_sismique?latlon={lon},{lat}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0].get("zone_sismicite", "Non disponible")
    except Exception as e:
        print(f"⚠ Erreur sismicité : {e}")
    return "Non disponible"

def fetch_rga(lat, lon):
    """
    Retrait-gonflement argiles : 
    https://georisques.gouv.fr/api/v1/rga?latlon={lon},{lat}
    Renvoie (exposition, codeExposition) ou (Non disponible, Non disponible).
    """
    if lat is None or lon is None:
        return ("Non disponible", "Non disponible")
    url = f"https://georisques.gouv.fr/api/v1/rga?latlon={lon},{lat}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return (
                data.get("exposition", "Non disponible"),
                data.get("codeExposition", "Non disponible")
            )
    except Exception as e:
        print(f"⚠ Erreur RGA : {e}")
    return ("Non disponible", "Non disponible")

### 3.3 : PCAET (ADEME)
def fetch_pcaet(code_insee):
    """
    Plans Climat Air Énergie Territorial : https://data.ademe.fr/datasets/base-des-pcaet
    Requête plein texte sur {code_insee} dans 'q='
    """
    url = f"https://data.ademe.fr/api/records/1.0/search/?dataset=base-des-pcaet&q={code_insee}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("nhits", 0) > 0
    except Exception as e:
        print(f"⚠ Erreur PCAET pour {code_insee}: {e}")
    return False

### 3.4 : IRVE (Bornes recharge)
def fetch_bornes_irve(code_insee):
    """
    Bornes IRVE : https://opendata.reseaux-energies.fr/explore/dataset/bornes-irve/information/
    Requête plein texte '?q={code_insee}'
    """
    url = f"https://opendata.reseaux-energies.fr/api/records/1.0/search/?dataset=bornes-irve&q={code_insee}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return len(data.get("records", []))
    except Exception as e:
        print(f"⚠ Erreur IRVE pour {code_insee}: {e}")
    return 0

### 3.5 : France Chaleur Urbaine
def fetch_chaleur_eligibility(lat, lon):
    """
    https://france-chaleur-urbaine.beta.gouv.fr/api/v1/eligibility?lat=X&lon=Y
    Renvoie un JSON indiquant par ex. {"eligible": True/False, "distance": ...}
    """
    if lat is None or lon is None:
        return None
    url = "https://france-chaleur-urbaine.beta.gouv.fr/api/v1/eligibility"
    params = {"lat": lat, "lon": lon}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"⚠ Erreur France Chaleur Urbaine : {e}")
        return None

# -------------------------------------------------------------------------
# 4) CLASSIFICATION SFIL + LOGIQUE D'ADAPTATION SIMPLIFIEE
# -------------------------------------------------------------------------
def evaluate_adaptation_measures(data, risk_name):
    """
    Logique minimaliste : on considère 'adapté' si DICRIM ou PCAET est vrai.
    """
    has_dicrim = data.get("DICRIM Disponible", False)
    has_pcaet = data.get("PCAET", False)
    return bool(has_dicrim or has_pcaet)

# -------------------------------------------------------------------------
# 5) BOUCLE DE TRAITEMENT PRINCIPALE + CREATION CSV
# -------------------------------------------------------------------------
def fetch_risk_reports(com_codes, csv_output):
    rows = []

    for code in tqdm(com_codes, desc="Traitement des communes"):
        lat, lon = fetch_coordinates(code)
        row = {
            "Code INSEE": code,
            "Commune": "Inconnu",
            "Latitude": lat,
            "Longitude": lon
        }

        # --- 1) GeoRisques : DICRIM, radon, sismicité, RGA, rapport_risque
        row["DICRIM Disponible"] = fetch_dicrim(code)
        row["Potentiel radon"] = fetch_radon(code)

        # Sismicité, RGA
        if lat is not None and lon is not None:
            row["Zone sismicité"] = fetch_sismicite(lat, lon)
            rga_expo, rga_code = fetch_rga(lat, lon)
            row["RGA Exposition"] = rga_expo
            row["RGA Code"] = rga_code
        else:
            row["Zone sismicité"] = "Non disponible"
            row["RGA Exposition"] = "Non disponible"
            row["RGA Code"] = "Non disponible"

        # Rapport risques
        json_risque = fetch_resultats_rapport_risque(code)
        if json_risque:
            commune_info = json_risque.get("commune", {})
            row["Commune"] = commune_info.get("libelle", "Inconnu")
            row["Code Postal"] = commune_info.get("codePostal", "Inconnu")
            row["URL Rapport"] = json_risque.get("url", "Non disponible")

            risques_naturels = json_risque.get("risquesNaturels", {})
            risques_technologiques = json_risque.get("risquesTechnologiques", {})

            # On récupère le booléen 'present' pour inondation, séisme, etc.
            for rn in RISQUES_NATURELS:
                row[rn] = risques_naturels.get(rn, {}).get("present", False)
            for rt in RISQUES_TECHNOLOGIQUES:
                row[rt] = risques_technologiques.get(rt, {}).get("present", False)

        # --- 2) PCAET, IRVE
        row["PCAET"] = fetch_pcaet(code)
        row["Nombre bornes IRVE"] = fetch_bornes_irve(code)

        # --- 3) France Chaleur Urbaine
        fcu_data = fetch_chaleur_eligibility(lat, lon)
        if fcu_data:
            row["Chaleur_Urbaine_eligible"] = fcu_data.get("eligible", None)
            row["Chaleur_Urbaine_distance"] = fcu_data.get("distance", None)
        else:
            row["Chaleur_Urbaine_eligible"] = None
            row["Chaleur_Urbaine_distance"] = None

        # --- 4) Evaluation SFIL
        # Pour chaque risque SFIL, on crée SFIL_<risque>_present + SFIL_<risque>_adaptation
        for sfil_risk in ALL_SFIL_RISKS:
            # ex. 'inondation', 'séisme', 'retraitGonflementArgile'
            present = row.get(sfil_risk, False)
            row[f"SFIL_{sfil_risk}_present"] = present
            row[f"SFIL_{sfil_risk}_adaptation"] = (
                evaluate_adaptation_measures(row, sfil_risk) if present else False
            )

        # --- 5) On peut proposer 3 actions d'adaptation si un risque est présent
        # (ex. "mise en place de digues", "reboisement", etc.)
        risques_identifies = [
            r for r in ALL_SFIL_RISKS if row.get(r, False)
        ]
        actions_retenues = ACTIONS_ADAPTATION[:3] if risques_identifies else []
        for action in ACTIONS_ADAPTATION:
            row[action] = (action in actions_retenues)

        rows.append(row)

    # Conversion en DataFrame
    df = pd.DataFrame(rows)

    # Forcer la conversion en float (au cas où certaines lignes soient None)
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    # Export CSV
    df.to_csv(csv_output, index=False, encoding='utf-8')
    print(f"✅ CSV généré : {csv_output}")
    return df

# -------------------------------------------------------------------------
# 6) CREATION D'UNE CARTE FOLIUM
# -------------------------------------------------------------------------
def create_folium_map(df, output_html="map_interactive.html"):
    """
    Crée une carte Folium avec marqueurs (un par commune),
    popup affichant quelques infos (sismicité, radon, IRVE, etc.)
    """
    df_valid = df.dropna(subset=["Latitude", "Longitude"])
    if df_valid.empty:
        print("⚠ Aucune commune avec coordonnées valides.")
        return

    # Centre la carte sur la moyenne
    center_lat = df_valid["Latitude"].mean()
    center_lon = df_valid["Longitude"].mean()

    my_map = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    for _, row in df_valid.iterrows():
        lat, lon = row["Latitude"], row["Longitude"]
        # Construire la popup
        popup_html = f"""
        <b>{row.get('Commune', 'Inconnu')}</b> - INSEE: {row['Code INSEE']}<br>
        Zone sismicité: {row.get('Zone sismicité', 'N/A')}<br>
        RGA: {row.get('RGA Exposition', 'N/A')}<br>
        Radon: {row.get('Potentiel radon', 'N/A')}<br>
        DICRIM: {row.get('DICRIM Disponible', False)}<br>
        PCAET: {row.get('PCAET', False)}<br>
        Bornes IRVE: {row.get('Nombre bornes IRVE', 0)}<br>
        Chaleur Urbaine éligible: {row.get('Chaleur_Urbaine_eligible', 'N/A')}<br>
        Distance réseau: {row.get('Chaleur_Urbaine_distance', 'N/A')} m
        """
        folium.Marker(
            location=[lat, lon],
            tooltip=row.get("Commune", ""),
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(my_map)

    my_map.save(output_html)
    print(f"✅ Carte Folium enregistrée : {output_html}")

# -------------------------------------------------------------------------
# 7) EXEMPLE D'UTILISATION
# -------------------------------------------------------------------------
if __name__ == "__main__":
    input_csv = "v_commune_2024.csv"  # Fichier CSV local
    codes_insee = extract_com_column(input_csv, limit=5)
    if codes_insee:
        # 1) Collecte + CSV
        df_result = fetch_risk_reports(codes_insee, "resultats_risques_reels.csv")
        # 2) Carte Folium
        create_folium_map(df_result, "carte_interactive.html")
    else:
        print("Aucun code INSEE trouvé dans le fichier CSV.")
