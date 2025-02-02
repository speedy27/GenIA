import boto3
import json

# Initialiser le client OpenSearch
opensearch = boto3.client('opensearch')

# Définition d'un schéma OpenAPI
openapi_schema = {
    "operationId": "getClimateRiskLambda",
    "description": "Retourne les risques climatiques pour une région donnée.",
    "apiPath": "/climate-risks",
    "httpMethod": "GET",
    "s3Path": "s3://sfil-openapi-schemas/climate_risk.yaml"
}

# Indexer le schéma OpenAPI dans OpenSearch
response = opensearch.index(
    index="openapi-index",
    id="1",
    body=json.dumps(openapi_schema)
)

print("✅ Schéma OpenAPI ajouté dans OpenSearch !")
