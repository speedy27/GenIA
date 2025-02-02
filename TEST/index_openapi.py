import boto3
import json

# Initialiser le client OpenSearch
opensearch = boto3.client('opensearch')

# Définition du mapping de l'index
index_name = "openapi-index"
mapping = {
    "mappings": {
        "properties": {
            "operationId": {"type": "keyword"},
            "description": {"type": "text"},
            "apiPath": {"type": "keyword"},
            "httpMethod": {"type": "keyword"},
            "s3Path": {"type": "keyword"}
        }
    }
}

# Création de l’index OpenSearch
response = opensearch.index(
    index=index_name,
    body=json.dumps(mapping)
)

print("✅ Index OpenSearch créé avec succès !")
