import boto3
import json

# Clients AWS
lambda_client = boto3.client("lambda")

def invoke_lambda(lambda_name, parameters):
    response = lambda_client.invoke(
        FunctionName=lambda_name,
        Payload=json.dumps({"parameters": parameters})
    )
    return json.loads(response["Payload"].read())

def get_climate_risks(region):
    return invoke_lambda("getClimateRiskLambda", [{"name": "region", "value": region}])

def simulate_risk_cost(risk_type):
    return invoke_lambda("simulateRiskCostLambda", [{"name": "risk_type", "value": risk_type}])

def get_regulations(query_text):
    return invoke_lambda("getRegulationInfoLambda", [{"name": "query_text", "value": query_text}])
