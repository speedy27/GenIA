# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 20:44:09 2025

@author: flori
"""

# -*- coding: utf-8 -*-
"""
Script complet + Parallélisme (ThreadPoolExecutor) pour accélérer la collecte.
APIs réelles : GeoRisques, ADEME (PCAET), IRVE, France Chaleur Urbaine.
"""

import requests
import pandas as pd
import folium
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------------------------------
# 1) LISTES DE RISQUES ET ACTIONS
# -------------------------------------------------------------------------
RISQUES_NATURELS = [
    "inondation",
    "séisme",
    "mouvementTerrain",
    "retraitGonflementArgile",
    "radon"
]
RISQUES_TECHNOLOGIQUES = [
    "icpe",
    "nucleaire",
    "canalisationsMatieresDangereuses",
    "pollutionSols"
]

ACTIONS_ADAPTATION = [
    "mise en place de digues",
    "reboisement",
    "zones tampons",
    "gestion des eaux pluviales",
    "aménagement du territoire",
    "réduction des émissions de gaz à effet de serre",
    "renforcement des infrastructures",
    "systèmes d’alerte précoce",
    "éducation et sensibilisation"
]

# -------------------------------------------------------------------------
# 2) UTILITAIRE POUR LIRE LE CSV
# -------------------------------------------------------------------------
def extract_com_column(file_path, limit=None):
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
        print(f"❌ Erreur lecture CSV : {e}")
        return []

# -------------------------------------------------------------------------
# 3) FONCTIONS D'APPELS D'API REELLES
# -------------------------------------------------------------------------
def fetch_coordinates(code_insee):
    url = f"https://geo.api.gouv.fr/communes/{code_insee}?fields=centre"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "centre" in data and "coordinates" in data["centre"]:
                lon, lat = map(float, data["centre"]["coordinates"])
                return float(lat), float(lon)
    except:
        pass
    return None, None

def fetch_resultats_rapport_risque(code_insee):
    url = f"https://www.georisques.gouv.fr/api/v1/resultats_rapport_risque?code_insee={code_insee}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def fetch_dicrim(code_insee):
    url = f"https://georisques.gouv.fr/api/v1/gaspar/dicrim?code_insee={code_insee}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("total", 0) > 0
    except:
        return False

def fetch_radon(code_insee):
    url = f"https://georisques.gouv.fr/api/v1/radon?code_insee={code_insee}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("potentielRadon", "Non disponible")
    except:
        return "Non disponible"

def fetch_sismicite(lat, lon):
    if lat is None or lon is None:
        return "Non disponible"
    url = f"https://georisques.gouv.fr/api/v1/zonage_sismique?latlon={lon},{lat}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0].get("zone_sismicite", "Non disponible")
    except:
        pass
    return "Non disponible"

def fetch_rga(lat, lon):
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
    except:
        pass
    return ("Non disponible", "Non disponible")

def fetch_pcaet(code_insee):
    url = f"https://data.ademe.fr/api/records/1.0/search/?dataset=base-des-pcaet&q={code_insee}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("nhits", 0) > 0
    except:
        pass
    return False

def fetch_bornes_irve(code_insee):
    url = f"https://opendata.reseaux-energies.fr/api/records/1.0/search/?dataset=bornes-irve&q={code_insee}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return len(data.get("records", []))
    except:
        pass
    return 0

def fetch_chaleur_eligibility(lat, lon):
    if lat is None or lon is None:
        return None
    url = "https://france-chaleur-urbaine.beta.gouv.fr/api/v1/eligibility"
    params = {"lat": lat, "lon": lon}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

# -------------------------------------------------------------------------
# 4) LOGIQUE D'ADAPTATION
# -------------------------------------------------------------------------
def evaluate_adaptation_measures(data, risk_name):
    has_dicrim = data.get("DICRIM Disponible", False)
    has_pcaet = data.get("PCAET", False)
    return bool(has_dicrim or has_pcaet)

# -------------------------------------------------------------------------
# 5) COLLECTE POUR UNE COMMUNE (FONCTION UNITAIRE)
# -------------------------------------------------------------------------
def collect_data_for_insee(code_insee):
    """
    Renvoie un dictionnaire 'row' avec toutes les infos pour la commune 
    identifiée par code_insee.
    """
    lat, lon = fetch_coordinates(code_insee)

    row = {
        "Code INSEE": code_insee,
        "Commune": "Inconnu",
        "Latitude": lat,
        "Longitude": lon
    }

    # A) GeoRisques
    row["DICRIM Disponible"] = fetch_dicrim(code_insee)
    row["Potentiel radon"] = fetch_radon(code_insee)

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
    rapport_data = fetch_resultats_rapport_risque(code_insee)
    if rapport_data:
        commune_info = rapport_data.get("commune", {})
        row["Commune"] = commune_info.get("libelle", "Inconnu")
        row["Code Postal"] = commune_info.get("codePostal", "Inconnu")
        row["URL Rapport"] = rapport_data.get("url", "Non disponible")

        risques_naturels = rapport_data.get("risquesNaturels", {})
        risques_technologiques = rapport_data.get("risquesTechnologiques", {})

        for rn in RISQUES_NATURELS:
            row[rn] = risques_naturels.get(rn, {}).get("present", False)
        for rt in RISQUES_TECHNOLOGIQUES:
            row[rt] = risques_technologiques.get(rt, {}).get("present", False)

    # B) PCAET, IRVE
    row["PCAET"] = fetch_pcaet(code_insee)
    row["Nombre bornes IRVE"] = fetch_bornes_irve(code_insee)

    # C) Chaleur urbaine
    fcu_data = fetch_chaleur_eligibility(lat, lon)
    if fcu_data:
        row["Chaleur_Urbaine_eligible"] = fcu_data.get("eligible", None)
        row["Chaleur_Urbaine_distance"] = fcu_data.get("distance", None)
    else:
        row["Chaleur_Urbaine_eligible"] = None
        row["Chaleur_Urbaine_distance"] = None

    # D) Évaluation "présence / adaptation" pour chaque risque
    for r_naturel in RISQUES_NATURELS:
        present = row.get(r_naturel, False)
        row[f"SFIL_{r_naturel}_present"] = present
        row[f"SFIL_{r_naturel}_adaptation"] = evaluate_adaptation_measures(row, r_naturel) if present else False

    for r_techno in RISQUES_TECHNOLOGIQUES:
        present = row.get(r_techno, False)
        row[f"SFIL_{r_techno}_present"] = present
        row[f"SFIL_{r_techno}_adaptation"] = evaluate_adaptation_measures(row, r_techno) if present else False

    # E) Proposer des actions d'adaptation (3 actions si un risque est présent)
    risques_identifies = [
        r for r in (RISQUES_NATURELS + RISQUES_TECHNOLOGIQUES)
        if row.get(r, False)
    ]
    actions_retenues = ACTIONS_ADAPTATION[:3] if risques_identifies else []
    for action in ACTIONS_ADAPTATION:
        row[action] = (action in actions_retenues)

    return row

# -------------------------------------------------------------------------
# 6) FONCTION PRINCIPALE : PARALLÉLISME AVEC ThreadPoolExecutor
# -------------------------------------------------------------------------
def fetch_risk_reports_parallel(com_codes, csv_output, max_workers=5):
    """
    Exécute la collecte de données pour chaque code INSEE 
    en parallèle (max_workers threads).
    """
    rows = []
    from concurrent.futures import as_completed

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_code = {
            executor.submit(collect_data_for_insee, code_insee): code_insee 
            for code_insee in com_codes
        }

        # as_completed renvoie les futures au fur et à mesure qu'elles se terminent
        for future in tqdm(as_completed(future_to_code), total=len(com_codes), desc="Collecte en parallèle"):
            code_insee = future_to_code[future]
            try:
                row = future.result()
                rows.append(row)
            except Exception as e:
                print(f"Erreur pour la commune {code_insee} : {e}")

    # Construction du DataFrame
    df = pd.DataFrame(rows)

    # Forcer latitude/longitude en float
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df.to_csv(csv_output, index=False, encoding='utf-8')
    print(f"✅ CSV généré : {csv_output}")

    return df

# -------------------------------------------------------------------------
# 7) CREATION D'UNE CARTE FOLIUM
# -------------------------------------------------------------------------
def create_folium_map(df, output_html="map_interactive.html"):
    df_valid = df.dropna(subset=["Latitude", "Longitude"])
    if df_valid.empty:
        print("⚠ Aucune commune avec coordonnées valides.")
        return

    center_lat = df_valid["Latitude"].mean()
    center_lon = df_valid["Longitude"].mean()
    my_map = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    for _, row in df_valid.iterrows():
        lat, lon = row["Latitude"], row["Longitude"]
        popup_html = f"""
        <b>{row.get('Commune', 'Inconnu')}</b> - INSEE: {row['Code INSEE']}<br>
        Sismicité: {row.get('Zone sismicité', 'N/A')}<br>
        RGA: {row.get('RGA Exposition', 'N/A')}<br>
        Radon: {row.get('Potentiel radon', 'N/A')}<br>
        DICRIM: {row.get('DICRIM Disponible', False)}<br>
        PCAET: {row.get('PCAET', False)}<br>
        IRVE: {row.get('Nombre bornes IRVE', 0)}<br>
        Elig. Chaleur: {row.get('Chaleur_Urbaine_eligible', 'N/A')}<br>
        Dist. Réseau: {row.get('Chaleur_Urbaine_distance', 'N/A')} m
        """
        folium.Marker(
            location=[lat, lon],
            tooltip=row.get("Commune", ""),
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(my_map)

    my_map.save(output_html)
    print(f"✅ Carte Folium enregistrée : {output_html}")

# -------------------------------------------------------------------------
# 8) EXEMPLE D’UTILISATION
# -------------------------------------------------------------------------
if __name__ == "__main__":
    input_csv = "v_commune_2024.csv"  # Fichier local avec col. COM
    com_codes = extract_com_column(input_csv, limit=5)
    if com_codes:
        # 1) Collecte en parallèle
        csv_output = "resultats_risques_reels_parallel.csv"
        df_result = fetch_risk_reports_parallel(com_codes, csv_output, max_workers=5)

        # 2) Carte Folium
        create_folium_map(df_result, "carte_interactive.html")
    else:
        print("Aucun code INSEE trouvé dans le CSV.")

