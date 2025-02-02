import boto3
import json

# Initialiser le client Bedrock
bedrock = boto3.client("bedrock-runtime")

# Question posée à l’agent
question = "Quels sont les plans d’adaptation en Île-de-France ?"

# Envoi de la requête à Bedrock
response = bedrock.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": [{"text": question}]}],
    inferenceConfig={"maxTokens": 2000, "temperature": 0}
)

# Affichage de la réponse
print("✅ Réponse de l'agent Bedrock :")
print(response['output']['message']['content'][0]['text'])
