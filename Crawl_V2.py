import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import hashlib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from fpdf import FPDF

# Configuration
BASE_URL = "https://www.data.gouv.fr/fr/datasets/"
OUTPUT_DIR = "./documents"
ERROR_LOG = "error_log.txt"
MAX_RETRIES = 3
MAX_WORKERS = 5

# Créer un dossier pour stocker les fichiers téléchargés
os.makedirs(OUTPUT_DIR, exist_ok=True)

DOCUMENT_TYPES = [
    "DICRIM", "PCS", "PLU", "PPRN", "PCAET", "SCoT", "PLUi", "PICS", "DDRM", "SRADDET"
]

# Configurer la session avec gestion des retries
session = requests.Session()
retries = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

# Gestion des erreurs
def log_error(message):
    with open(ERROR_LOG, 'a') as log_file:
        log_file.write(message + "\n")

# Nettoyer les noms de fichiers pour Windows
def sanitize_filename(filename):
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    return filename if filename.strip() else "fichier_inconnu"

def hash_file(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()

def download_file(url, output_folder, downloaded_hashes):
    try:
        filename = sanitize_filename(url.split('/')[-1])
        local_filename = os.path.join(output_folder, filename)

        # Vérifier que le dossier existe
        os.makedirs(output_folder, exist_ok=True)

        response = session.get(url, stream=True, timeout=10)
        response.raise_for_status()

        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_hash = hash_file(local_filename)
        if file_hash in downloaded_hashes:
            os.remove(local_filename)
            print(f"Doublon supprimé : {local_filename}")
        else:
            downloaded_hashes.add(file_hash)
            print(f"Fichier téléchargé : {local_filename}")
            return local_filename

    except (requests.RequestException, OSError) as e:
        log_error(f"Erreur lors du téléchargement de {url} : {e}")
        return None

def find_and_download_files(commune_name, file_types=["pdf", "json", "csv"]):
    commune_folder = os.path.join(OUTPUT_DIR, sanitize_filename(commune_name))
    os.makedirs(commune_folder, exist_ok=True)
    downloaded_hashes = set()
    downloaded_summary = []

    search_url = f"https://www.data.gouv.fr/fr/search/?q={commune_name}"
    try:
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        links = [a['href'] for a in soup.find_all('a', href=True) if '/datasets/' in a['href']]
        unique_links = list(set(links))

        print(f"Trouvé {len(unique_links)} jeux de données pour {commune_name}.")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_url = {
                executor.submit(download_file, urljoin(BASE_URL, link), commune_folder, downloaded_hashes): link
                for link in unique_links if link.strip()
            }

            for future in as_completed(future_to_url):
                try:
                    file_path = future.result()
                    if file_path:
                        downloaded_summary.append(file_path)
                except Exception as e:
                    log_error(f"Erreur lors de la récupération du fichier : {e}")

    except requests.RequestException as e:
        log_error(f"Erreur lors de la recherche pour {commune_name} : {e}")

    summary_file = os.path.join(commune_folder, "download_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(downloaded_summary, f, indent=4)

    export_to_excel(commune_folder, downloaded_summary)
    export_to_pdf(commune_folder, downloaded_summary)

def export_to_excel(folder, data):
    df = pd.DataFrame({"Fichiers": data})
    excel_file = os.path.join(folder, "summary.xlsx")
    df.to_excel(excel_file, index=False)

def export_to_pdf(folder, data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Rapport de Téléchargement", ln=True, align='C')
    for item in data:
        pdf.cell(200, 10, txt=item, ln=True)
    pdf_file = os.path.join(folder, "summary.pdf")
    pdf.output(pdf_file)

if __name__ == "__main__":
    communes = [
        "Paris", "Lyon", "Marseille", "Toulouse", "Nice"
    ]  # Limité à 5 pour test rapide

    for commune in communes:
        find_and_download_files(commune)
