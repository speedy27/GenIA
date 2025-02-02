import json
import boto3

# 🔹 Initialisation du client DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ClimateRisks')

def lambda_handler(event, context):
    # 🔹 Récupération de la région demandée
    region = event["parameters"][0]["value"]

    try:
        # 🔹 Recherche des risques dans DynamoDB
        response = table.get_item(Key={"region": region})
        risks = response.get("Item", {}).get("risks", "Aucun risque trouvé.")

        return {
            "statusCode": 200,
            "body": json.dumps({"region": region, "risks": risks})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
