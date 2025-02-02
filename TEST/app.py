import streamlit as st
from chatbot_ui import chatbot_section
from map_ui import map_section # type: ignore

# Configuration de la page
st.set_page_config(page_title="SFIL - Risques Climatiques", layout="wide")

st.title("🌍 SFIL - Plateforme IA de Gestion des Risques Climatiques")

# Onglets : Chatbot et Carte Interactive
tab1, tab2 = st.tabs(["🤖 Chatbot IA", "🗺️ Carte Interactive"])

with tab1:
    chatbot_section()

with tab2:
    map_section()
