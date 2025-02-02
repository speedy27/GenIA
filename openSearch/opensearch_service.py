from opensearchpy import OpenSearch
import boto3
import json

# Connexion à OpenSearch
client = OpenSearch(
    hosts=[{'host': 'your-opensearch-endpoint', 'port': 443}],
    http_auth=('admin', 'password')
)

# Connexion AWS Lambda
lambda_client = boto3.client('lambda')

# 📌 Indexer une API dans OpenSearch
def index_api(api_id, description, api_path, http_method, lambda_function):
    doc = {
        "operationId": api_id,
        "description": description,
        "apiPath": api_path,
        "httpMethod": http_method,
        "lambdaFunction": lambda_function
    }
    client.index(index="api-index", id=api_id, body=doc)
    print(f"✅ API {api_id} indexée avec succès.")

# 📌 Indexer un document pour le RAG (Recherche Documentaire)
def index_document(doc_id, title, content, category):
    doc = {
        "title": title,
        "content": content,
        "category": category
    }
    client.index(index="kb-index", id=doc_id, body=doc)
    print(f"✅ Document {title} indexé.")

# 📌 Rechercher une API en fonction d’une requête utilisateur
def search_api(query):
    search_body = {"query": {"match": {"description": query}}}
    response = client.search(index="api-index", body=search_body)
    
    if response["hits"]["total"]["value"] > 0:
        return response["hits"]["hits"][0]["_source"]
    return None

# 📌 Rechercher un document dans la KB
def search_knowledge_base(query):
    search_body = {"query": {"match": {"content": query}}}
    response = client.search(index="kb-index", body=search_body)

    if response["hits"]["total"]["value"] > 0:
        return response["hits"]["hits"][0]["_source"]
    return None

# 📌 Fonction principale qui gère la requête utilisateur
def process_user_query(query):
    # Vérifier si la réponse est dans la KB (RAG)
    kb_result = search_knowledge_base(query)
    if kb_result:
        return f"📚 Réponse trouvée dans la KB : {kb_result['content']}"

    # Si aucune réponse en KB, chercher une API correspondante
    api_info = search_api(query)
    if api_info:
        print(f"🔗 API trouvée : {api_info['operationId']}, appel de la Lambda {api_info['lambdaFunction']}")
        
        # Appeler la Lambda associée
        response = lambda_client.invoke(
            FunctionName=api_info['lambdaFunction'],
            InvocationType='RequestResponse',
            Payload=json.dumps({"query": query})
        )
        
        lambda_response = json.loads(response['Payload'].read())
        return f"⚡ Réponse API : {lambda_response['result']}"

    return "❌ Désolé, aucune réponse trouvée."

# 📌 Exemple d'utilisation
if __name__ == "__main__":
    user_query = "Quels sont les risques climatiques pour Paris en 2050 ?"
    response = process_user_query(user_query)
    print(response)
