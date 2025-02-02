import json
import boto3
from opensearchpy import OpenSearch

host = "search-climate-risks-opensearch.us-west-2.es.amazonaws.com"
index_name = "climate_adaptation"
auth = ("admin", "password")

client = OpenSearch(
    hosts=[{"host": host, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True
)

def lambda_handler(event, context):
    query_params = event.get("queryStringParameters", {})
    keyword = query_params.get("keyword", "")

    search_query = {
        "query": {
            "match": {
                "measures": keyword
            }
        }
    }

    response = client.search(index=index_name, body=search_query)
    return {
        "statusCode": 200,
        "body": json.dumps(response["hits"]["hits"])
    }
