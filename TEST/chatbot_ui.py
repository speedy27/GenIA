import streamlit as st
import boto3
import json

# Initialiser le client AWS Bedrock
bedrock = boto3.client("bedrock-runtime")

def chatbot_section():
    st.subheader("🤖 Chatbot IA - Posez vos questions")
    
    # Champ de texte pour la question utilisateur
    user_input = st.text_input("Entrez votre question :", "")

    if st.button("Envoyer"):
        if user_input:
            response = bedrock.converse(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                messages=[{"role": "user", "content": [{"text": user_input}]}],
                inferenceConfig={"maxTokens": 2000, "temperature": 0}
            )

            st.success("✅ Réponse de l'IA :")
            st.write(response['output']['message']['content'][0]['text'])
        else:
            st.warning("Veuillez entrer une question.")
