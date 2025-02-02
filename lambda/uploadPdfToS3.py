
# probleme : il faut ajouter des layers adapter pour la lambda function, hors proposition d'aws
# pour résume la function permet aux users de televerser un fichier pdf, le code va extraire le texte du pdf, 
# le resumer et l'indexer avec faiss et titan embeddings

import boto3
import os
import tempfile
import json
import base64
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

s3_client = boto3.client('s3')
BUCKET_NAME = "sfil-documents-bucket"
S3_FOLDER = "UploadsFront"

def lambda_handler(event, context):
    try:
        # Extraction des données de l'event
        body = json.loads(event["body"])
        file_name = body.get("file_name", "uploaded.pdf")
        file_content_base64 = body.get("file_content")

        if not file_content_base64:
            return {"statusCode": 400, "body": json.dumps({"error": "Le fichier est manquant."})}

        # Décodage du  PDF en Base64
        file_content = base64.b64decode(file_content_base64)

        # Sauvegarde temporaire 
        temp_file_path = f"/tmp/{file_name}"
        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        # Upload vers notre S3
        s3_key = f"{S3_FOLDER}/{file_name}"
        s3_client.upload_file(temp_file_path, BUCKET_NAME, s3_key)

        # Extraction du texte du PDF avc pdfreader
        reader = PdfReader(temp_file_path)
        full_text = " ".join(page.extract_text() for page in reader.pages if page.extract_text())

        # Résumé du texte avec Mistral 7x8b
        summary = summarize_text(full_text)

        # Indexation du document avec FAISS et Titan Embeddings
        index_status = embed_and_index(full_text, file_name)

        os.remove(temp_file_path)  # Suppression du fichier temporaire

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Fichier traité avec succès chackal",
                "summary": summary,
                "index_status": index_status,
                "s3_location": f"s3://{BUCKET_NAME}/{s3_key}"
            })
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# Résumé avec Mistral
def summarize_text(text):
    bedrock_client = boto3.client('bedrock', region_name='us-west-2')
    model_arn = "arn:aws:bedrock:us-west-2::foundation-model/mistral.mixtral-8x7b-instruct"

    try:
        response = bedrock_client.invoke_model(
            modelId=model_arn,
            contentType="application/json",
            body=json.dumps({"text": text})
        )
        result = json.loads(response["body"])
        return result.get("generated_text", "Résumé non disponible")
    except Exception as e:
        return f"Erreur lors du résumé : {str(e)}"

# Indexation avec FAISS et Titan
def embed_and_index(text, file_name):
    bedrock_client = boto3.client('bedrock', region_name='us-west-2')
    model_arn = "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embeddings-text-v2"

    chunks = [text[i:i+512] for i in range(0, len(text), 512)]
    embeddings = []

    try:
        for chunk in chunks:
            response = bedrock_client.invoke_model(
                modelId=model_arn,
                contentType="application/json",
                body=json.dumps({"text": chunk})
            )
            result = json.loads(response["body"])
            embedding = result.get("embedding", [])
            embeddings.append(embedding)

        # Conversion en matrice numpy pour FAISS
        import numpy as np
        embedding_matrix = np.array(embeddings)

        # Indexer dans FAISS
        index = faiss.IndexFlatL2(embedding_matrix.shape[1])
        index.add(embedding_matrix)

        # Sauvegarde de l'index dans S3
        index_file = f"/tmp/{file_name}.index"
        faiss.write_index(index, index_file)
        s3_client.upload_file(index_file, BUCKET_NAME, f"{S3_FOLDER}/{file_name}.index")
        os.remove(index_file)

        return "Indexation réussie"

    except Exception as e:
        return f"Erreur lors de l'indexation : {str(e)}"

