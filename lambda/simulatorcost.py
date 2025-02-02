

import json

def lambda_handler(event, context):
    body = json.loads(event["body"])
    city = body.get("city")
    risk_type = body.get("risk_type")

    cost_factors = {
        "inondation": 1000000,
        "feu de forêt": 750000,
        "sécheresse": 500000
    }

    cost = cost_factors.get(risk_type, 200000) * 1.2  # Ajout d'un facteur de sécurité

    return {
        "statusCode": 200,
        "body": json.dumps({
            "city": city,
            "risk_type": risk_type,
            "estimated_cost": cost
        })
    }
