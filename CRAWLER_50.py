import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

# Configuration
BASE_URL = "https://www.data.gouv.fr/fr/datasets/"
OUTPUT_DIR = "E:\HGENIA"

# Créer un dossier pour stocker les fichiers téléchargés
os.makedirs(OUTPUT_DIR, exist_ok=True)

DOCUMENT_TYPES = [
    "DICRIM", "PCS", "PLU", "PPRN", "PCAET", "SCoT", "PLUi", "PICS", "DDRM", "SRADDET"
]

EXTRA_URLS = [
    "https://www.geoportail-urbanisme.gouv.fr",
    "https://www.georisques.gouv.fr",
    "https://www.insee.fr",
    "https://www.urbanisme.gouv.fr"
]

def download_file(url, output_folder, downloaded_files):
    local_filename = os.path.join(output_folder, url.split('/')[-1])
    if local_filename in downloaded_files:
        print(f"Fichier déjà téléchargé : {local_filename}")
        return None
    try:
        with requests.get(url, stream=True, timeout=10) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        downloaded_files.add(local_filename)
        print(f"Fichier téléchargé : {local_filename}")
        return local_filename
    except requests.RequestException as e:
        print(f"Erreur lors du téléchargement de {url} : {e}")
        return None

def find_and_download_files(commune_name, file_types=["pdf", "json", "csv"]):
    commune_folder = os.path.join(OUTPUT_DIR, commune_name)
    os.makedirs(commune_folder, exist_ok=True)
    downloaded_files = set(os.listdir(commune_folder))
    downloaded_summary = []

    # Rechercher la commune sur data.gouv.fr
    search_url = f"https://www.data.gouv.fr/fr/search/?q={commune_name}"
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraire les liens des datasets
        links = [a['href'] for a in soup.find_all('a', href=True) if '/datasets/' in a['href']]
        unique_links = list(set(links))

        print(f"Trouvé {len(unique_links)} jeux de données pour {commune_name}.")

        # Parcourir chaque lien et rechercher des fichiers à télécharger
        for link in unique_links:
            full_link = urljoin(BASE_URL, link)
            try:
                dataset_page = requests.get(full_link, timeout=10)
                dataset_page.raise_for_status()
                dataset_soup = BeautifulSoup(dataset_page.content, 'html.parser')

                for file_type in file_types:
                    files = dataset_soup.find_all('a', href=True)
                    for file in files:
                        file_url = file['href']
                        if file_url.endswith(f".{file_type}"):
                            file_path = download_file(urljoin(BASE_URL, file_url), commune_folder, downloaded_files)
                            if file_path:
                                downloaded_summary.append(file_path)
            except requests.RequestException as e:
                print(f"Erreur lors de l'accès à {full_link} : {e}")
                continue

        # Rechercher des fichiers via Google Dorks
        google_dorks(commune_name, file_types)

    except requests.RequestException as e:
        print(f"Erreur lors de la recherche pour {commune_name} : {e}")

    # Générer un fichier de résumé des téléchargements
    summary_file = os.path.join(commune_folder, "download_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(downloaded_summary, f, indent=4)

def google_dorks(commune_name, file_types):
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
                print(f"Requête Google Dork : {dork_query}")
                # Ici, on ne peut pas interroger directement Google sans API officielle
                # On affiche la requête pour une utilisation manuelle

if __name__ == "__main__":
    communes = [
        "Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille",
        "Rennes", "Reims", "Le Havre", "Saint-Étienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nîmes", "Villeurbanne",
        "Clermont-Ferrand", "Le Mans", "Aix-en-Provence", "Brest", "Tours", "Amiens", "Limoges", "Annecy", "Boulogne-Billancourt", "Perpignan",
        "Metz", "Besançon", "Orléans", "Mulhouse", "Rouen", "Caen", "Nancy", "Saint-Denis", "Argenteuil", "Montreuil",
        "Avignon", "Poitiers", "Versailles", "Courbevoie", "Asnières-sur-Seine", "Colombes", "Aulnay-sous-Bois", "Saint-Paul", "Fort-de-France", "Créteil"
    ]

    for commune in communes:
        find_and_download_files(commune)
