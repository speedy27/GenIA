import boto3
import json

# Initialiser le client OpenSearch
opensearch = boto3.client('opensearch')

# Définition de la requête de recherche
query = {
    "query": {
        "match": {
            "description": "risques climatiques"
        }
    }
}

# Effectuer la recherche dans OpenSearch
response = opensearch.search(index="openapi-index", body=query)

# Afficher les résultats
print("✅ Résultats de la recherche :")
print(json.dumps(response, indent=4))
