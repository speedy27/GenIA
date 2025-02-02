import json
import boto3

bedrock_client = boto3.client('bedrock-runtime', region_name='us-west-2')

def lambda_handler(event, context):
    body = json.loads(event["body"])
    document_text = body.get("text", "")

    if not document_text:
        return {"statusCode": 400, "body": json.dumps({"error": "Aucun texte fourni"})}

    response = bedrock_client.invoke_model(
        modelId="arn:aws:bedrock:us-west-2::foundation-model/mistral.mixtral-8x7b-instruct",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": document_text, "maxTokens": 500})
    )

    result = json.loads(response["body"])
    return {
        "statusCode": 200,
        "body": json.dumps({"summary": result["generated_text"]})
    }
