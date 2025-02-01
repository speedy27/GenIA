
import requests
import os
import zipfile
import shutil
from tqdm import tqdm  # Barre de progression
from concurrent.futures import ThreadPoolExecutor

"""
Ce script permet de :
1️⃣ Télécharger des documents **PLUi** (Plans Locaux d'Urbanisme intercommunaux) au format ZIP via l'API Géoportail de l'Urbanisme.
2️⃣ Décompresser ces fichiers ZIP pour extraire les fichiers contenus.
3️⃣ Parcourir les sous-répertoires et récupérer uniquement les fichiers **PDF**.
4️⃣ Supprimer les fichiers ZIP et les répertoires extraits après extraction des PDF.

"""

# Base URL de l'API Géoportail de l'Urbanisme
BASE_URL = "https://www.geoportail-urbanisme.gouv.fr/api"

# Dossiers de sauvegarde et de travail
OUTPUT_DIR = "plui_documents"
UNZIPPED_DIR = "plui_extracted"
PDF_DIR = "pdf_extracted"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UNZIPPED_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

RESULTS_PER_PAGE = 50  

def get_plui_documents():
    """
    Récupère la liste de tous les documents PLUi via l'API, en gérant la pagination.
    :return: Liste des documents PLUi (id, nom, type).
    """
    page = 1
    all_documents = []

    while True:
        url = f"{BASE_URL}/document?documentType=PLUi&status=document.production&page={page}&limit={RESULTS_PER_PAGE}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            documents = response.json()

            if not documents:
                break  # Plus de documents à récupérer

            all_documents.extend(documents)
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des documents PLUi (page {page}) : {e}")
            break

    return all_documents

def download_and_process_document(doc):
    """
    Télécharge, décompresse, extrait les PDF et nettoie les fichiers d'un document PLUi donné.
    :param doc: Dictionnaire contenant {id, name}
    """
    doc_id = doc["id"]
    doc_name = doc["name"]
    zip_path = os.path.join(OUTPUT_DIR, f"{doc_name}.zip")
    extract_path = os.path.join(UNZIPPED_DIR, doc_name)

    # Vérification de l'existence du fichier ZIP
    if os.path.exists(zip_path):
        print(f"⏩ Fichier déjà téléchargé : {doc_name}.zip")
    else:
        url = f"{BASE_URL}/document/{doc_id}/download/{doc_name}.zip"
        try:
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            with open(zip_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
            print(f"✅ Téléchargé : {doc_name}.zip")
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors du téléchargement du PLUi ({doc_name}) : {e}")
            return

    # Décompression du fichier ZIP
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"✅ Décompressé : {doc_name}.zip")
    except zipfile.BadZipFile:
        print(f"❌ Erreur : {doc_name}.zip n'est pas un fichier ZIP valide.")
        return

    # Collecte des fichiers PDF
    pdf_files = []
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
    
    if pdf_files:
        print(f"📄 {len(pdf_files)} fichiers PDF trouvés pour {doc_name}. Copie en cours...")
        for pdf_path in pdf_files:
            shutil.copy2(pdf_path, PDF_DIR)
    else:
        print(f"⚠️ Aucun PDF trouvé pour {doc_name}.")
    
    # Suppression des fichiers ZIP et des dossiers extraits
    os.remove(zip_path)
    shutil.rmtree(extract_path, ignore_errors=True)
    print(f"🗑️ Nettoyage terminé pour {doc_name}.")

def download_and_process_all_plui():
    """
    Télécharge, traite et nettoie tous les documents PLUi en utilisant un pool de threads.
    """
    documents = get_plui_documents()
    if not documents:
        print("⚠️ Aucun document PLUi trouvé.")
        return

    print(f"🔍 {len(documents)} documents PLUi trouvés. Début du traitement...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(download_and_process_document, documents), total=len(documents), desc="Traitement des PLUi"))
    print("✅ Tous les documents PLUi ont été traités.")

download_and_process_all_plui()
