import requests
import os
import zipfile
import shutil
from tqdm import tqdm  # Barre de progression
from concurrent.futures import ThreadPoolExecutor

# Base URL de l'API Géoportail de l'Urbanisme
BASE_URL = "https://www.geoportail-urbanisme.gouv.fr/api"

# Dossiers de sauvegarde et de travail
OUTPUT_DIR = "plu_documents"
UNZIPPED_DIR = "plu_extracted"
PDF_DIR = "pdf_plu_extracted"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UNZIPPED_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Nombre de résultats par page (modifiable selon l'API)
RESULTS_PER_PAGE = 50  

def get_plu_documents():
    """
    Récupère la liste de tous les documents PLU via l'API, en gérant la pagination.
    :return: Liste des documents PLU (id, name).
    """
    page = 1
    all_documents = []

    while True:
        url = f"{BASE_URL}/document?documentType=PLU&status=document.production&page={page}&limit={RESULTS_PER_PAGE}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            documents = response.json()

            if not isinstance(documents, list):
                print("❌ Format inattendu des données reçues depuis l'API.")
                break

            if not documents:
                break  # Plus de documents à récupérer

            all_documents.extend(documents)
            page += 1

        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des documents PLU (page {page}) : {e}")
            break

    return all_documents

def download_and_process_document(doc):
    """
    Télécharge, décompresse, extrait les PDF et nettoie les fichiers d'un document PLU donné.
    :param doc: Dictionnaire contenant {id, name}
    """
    doc_id = doc.get("id")
    doc_name = doc.get("name")
    if not doc_id or not doc_name:
        print("⚠️ Document invalide reçu depuis l'API.")
        return
    
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
            print(f"❌ Erreur lors du téléchargement du PLU ({doc_name}) : {e}")
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
    pdf_files = [os.path.join(root, file) for root, _, files in os.walk(extract_path) for file in files if file.lower().endswith(".pdf")]
    
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

def download_and_process_all_plu():
    """
    Télécharge, traite et nettoie tous les documents PLU en séquentiel.
    """
    documents = get_plu_documents()
    if not documents:
        print("⚠️ Aucun document PLU trouvé.")
        return

    print(f"🔍 {len(documents)} documents PLU trouvés. Début du traitement...")
    for doc in tqdm(documents, desc="Traitement des PLU"):
        download_and_process_document(doc)
    print("✅ Tous les documents PLU ont été traités.")

# 🔥 Exécuter le script
download_and_process_all_plu()
