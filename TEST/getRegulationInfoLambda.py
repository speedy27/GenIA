import json
import boto3

# 🔹 Initialisation du client OpenSearch
opensearch = boto3.client('opensearch')

def lambda_handler(event, context):
    query_text = event["parameters"][0]["value"]

    query = {
        "query": {
            "match": {
                "content": query_text
            }
        }
    }

    response = opensearch.search(index="regulations-index", body=query)

    results = [hit["_source"]["content"] for hit in response["hits"]["hits"]]

    return {
        "statusCode": 200,
        "body": json.dumps({"query": query_text, "results": results})
    }
