# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 15:54:31 2025
@author: clean
"""
"""
Script génération des liens de téléchargement des docs DICRIM et ajout à un CSV pour les stocker et le réutiliser. 

"""

import pandas as pd
import requests
import csv
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm  # Barre de progression

# Base URL pour les DICRIM
BASE_URL = "https://files.georisques.fr/DICRIM/DICRIM_{code_insee}.pdf"

# Nom du fichier CSV
CSV_FILENAME = "resultats_dicrim.csv"

# Fichier source des codes INSEE
file_path = "C:\\Users\\clean\\OneDrive\\Documents\\Hackathon-GENIA\\v_commune_2024.csv"  

def extract_com_column(file_path):
    """
    Extrait la colonne 'COM' du fichier CSV contenant les codes INSEE.
    :param file_path: Chemin du fichier CSV
    :return: Liste des codes INSEE
    """
    try:
        df = pd.read_csv(file_path, dtype=str)  
        if "COM" in df.columns:
            return df["COM"].dropna().tolist()  
        else:
            print("❌ La colonne 'COM' n'existe pas dans ce fichier.")
            return []
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier : {e}")
        return []

def check_dicrim(code_insee):
    """
    Vérifie si un fichier DICRIM existe pour un code INSEE donné et retourne le statut.
    :param code_insee: Code INSEE de la commune
    :return: Tuple (code INSEE, URL DICRIM ou 'Non disponible')
    """
    url = BASE_URL.replace("{code_insee}", code_insee)

    try:
        response = requests.head(url, timeout=5)  
        if response.status_code == 200:
            return (code_insee, url)  
    except requests.exceptions.RequestException:
        pass  

    return (code_insee, "Non disponible")  

def save_results_to_csv(results, mode="a"):
    """
    Sauvegarde les résultats dans un fichier CSV, avec mise à jour régulière.
    :param results: Liste des tuples (code INSEE, lien DICRIM ou 'Non disponible')
    :param mode: Mode d'écriture, "a" pour ajouter à un fichier existant
    """
    file_exists = os.path.isfile(CSV_FILENAME)

    with open(CSV_FILENAME, mode=mode, newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists or mode == "w":
            writer.writerow(["Code INSEE", "Lien DICRIM"])  

        writer.writerows(results)  

def process_all_codes(codes_insee, update_interval=100):
    """
    Vérifie les DICRIM pour tous les codes INSEE extraits et enregistre les résultats.
    :param codes_insee: Liste des codes INSEE
    :param update_interval: Nombre d'entrées avant mise à jour du CSV
    """
    if not codes_insee:
        print("⚠️ Aucun code INSEE à traiter. Vérifiez le fichier source.")
        return

    results = []
    processed_count = 0  

    with ThreadPoolExecutor(max_workers=10) as executor:
        with tqdm(total=len(codes_insee), desc="🔍 Vérification DICRIM", unit="doc") as pbar:
            for result in executor.map(check_dicrim, codes_insee):
                results.append(result)
                pbar.update(1)
                processed_count += 1

                # Auto-save tous les 'update_interval' codes INSEE parcourus
                if processed_count % update_interval == 0:
                    save_results_to_csv(results)
                    results = []  # Réinitialiser la liste pour éviter d'écrire deux fois les mêmes données
                    print(f"📄 Sauvegarde intermédiaire après {processed_count} vérifications...")

    if results:
        save_results_to_csv(results)
        print(f"📄 Dernière sauvegarde effectuée avec succès.")

    print(f"✅ Résultats enregistrés dans {CSV_FILENAME}")


codes_insee = extract_com_column(file_path)  # Extraction des codes INSEE
process_all_codes(codes_insee)  