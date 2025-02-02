import boto3
import json

# Initialiser le client OpenSearch
opensearch = boto3.client('opensearch')

# Paramètres du domaine OpenSearch Serverless
domain_name = "sfil-opensearch"

# Création du cluster OpenSearch Serverless
response = opensearch.create_domain(
    DomainName=domain_name,
    EngineVersion="OpenSearch_2.11",
    ClusterConfig={
        "InstanceType": "t3.medium.search",
        "InstanceCount": 1
    },
    EBSOptions={
        "EBSEnabled": True,
        "VolumeSize": 10
    }
)

print("✅ Cluster OpenSearch créé avec succès !")
print(json.dumps(response, indent=4))
