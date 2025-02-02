import json
import boto3

# 📌 Connexion à DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ClimateRiskData')

def format_city_name(city):
    """ Convertir le nom de la ville en MAJUSCULES et retirer les caractères spéciaux """
    city = city.upper().strip()
    city = city.replace("-", " ").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ç", "C")
    return city

def lambda_handler(event, context):
    """ Fonction Lambda qui récupère les risques climatiques pour une ville donnée """
    
    # 📌 Récupération du paramètre (nom de la ville) et mise en forme
    city = event.get("queryStringParameters", {}).get("city", "")

    if not city:
        return {"statusCode": 400, "body": json.dumps({"error": "Paramètre 'city' manquant"})}

    formatted_city = format_city_name(city)  # Convertir en MAJUSCULES et normaliser

    # 📌 Rechercher directement dans DynamoDB
    response = table.scan(
        FilterExpression="city = :c",
        ExpressionAttributeValues={":c": formatted_city}
    )

    if response["Items"]:
        result = f"🌍 Risques pour {response['Items'][0]['city']} : {response['Items'][0]['risk_description']} (Année {response['Items'][0]['year']})"
    else:
        result = "❌ Aucun risque trouvé."

    return {
        "statusCode": 200,
        "body": json.dumps({"result": result})
    }
