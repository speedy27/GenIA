import boto3
import json

bedrock = boto3.client("bedrock-runtime")

message = {
    "role": "user",
    "content": [
        {"text": "Quels sont les risques climatiques pour Paris ?"}
    ]
}

response = bedrock.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[message],
    inferenceConfig={"maxTokens": 2000, "temperature": 0}
)

print("✅ Réponse de l'agent IA :")
print(response['output']['message']['content'][0]['text'])
