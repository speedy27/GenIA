import boto3
import json
import pytest

@pytest.fixture
def bedrock_client():
    return boto3.client("bedrock-runtime")

@pytest.fixture
def opensearch_client():
    return boto3.client("opensearch")

@pytest.fixture
def lambda_client():
    return boto3.client("lambda")

def test_full_pipeline(bedrock_client, opensearch_client, lambda_client):
    # Étape 1 : L'utilisateur pose une question
    question = "Quels sont les risques climatiques pour Paris ?"

    bedrock_response = bedrock_client.converse(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        messages=[{"role": "user", "content": [{"text": question}]}],
        inferenceConfig={"maxTokens": 2000, "temperature": 0}
    )

    # Étape 2 : OpenSearch récupère les informations associées
    query = {"query": {"match": {"description": "risques climatiques"}}}
    opensearch_response = opensearch_client.search(index="openapi-index", body=query)

    # Étape 3 : Lambda est invoquée avec la bonne région
    payload = json.dumps({"parameters": [{"name": "region", "value": "Île-de-France"}]})
    lambda_response = lambda_client.invoke(
        FunctionName="getClimateRiskLambda",
        Payload=payload
    )

    response_payload = json.loads(lambda_response["Payload"].read())

    # Vérification des résultats
    assert "risques climatiques" in bedrock_response['output']['message']['content'][0]['text']
    assert opensearch_response["hits"]["total"]["value"] > 0
    assert "risks" in response_payload["body"]
