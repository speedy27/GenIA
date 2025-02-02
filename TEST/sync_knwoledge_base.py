import boto3
import json

# Initialiser le client OpenSearch
opensearch = boto3.client('opensearch')

# Document sur les risques climatiques
document = {
    "title": "Rapport Climat 2050",
    "content": "Les inondations et vagues de chaleur augmenteront de 30% d’ici 2050.",
    "tags": ["risques", "climat"]
}

# Indexer dans OpenSearch
response = opensearch.index(index="climate-kb", body=document)

print("✅ Base de connaissances mise à jour !")
