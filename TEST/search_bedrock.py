import boto3
import json

# Initialiser les clients Bedrock et OpenSearch
bedrock = boto3.client("bedrock-runtime")
opensearch = boto3.client("opensearch")

# Requête utilisateur
user_query = "Quels sont les risques climatiques pour Paris ?"

# Recherche dans OpenSearch pour trouver la bonne API
query = {"query": {"match": {"description": user_query}}}
search_results = opensearch.search(index="openapi-index", body=query)

# Récupération des résultats
if search_results["hits"]["total"]["value"] > 0:
    action = search_results["hits"]["hits"][0]["_source"]
    api_path = action["apiPath"]
    operation_id = action["operationId"]
else:
    api_path = "Aucune API trouvée"
    operation_id = "unknown"

# Envoyer la requête à Bedrock
message = {
    "role": "user",
    "content": [
        {"text": f"L'API {operation_id} correspond à votre question."},
        {"text": f"Vous pouvez l'appeler avec l'URL : {api_path}."}
    ]
}

response = bedrock.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[message],
    inferenceConfig={"maxTokens": 2000, "temperature": 0}
)

print("✅ Réponse de l'agent IA :")
print(response['output']['message']['content'][0]['text'])
