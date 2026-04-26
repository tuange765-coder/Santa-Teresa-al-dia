import streamlit as st
from sqlalchemy import create_engine, text

# --- CONEXIÓN LIMPIA ---
# Asegúrate de que NO haya espacios antes o después de las comillas
URL_NEON = "AQUÍ_TU_ENLACE_CORREGIDO"

# Este bloque intenta conectar y te avisa si algo falla antes de romper la página
try:
    # Limpiamos espacios en blanco por si acaso
    URL_NEON = URL_NEON.strip()
    
    # Forzamos que use el driver correcto
    if URL_NEON.startswith("postgres://"):
        URL_NEON = URL_NEON.replace("postgres://", "postgresql+psycopg2://", 1)
        
    engine = create_engine(URL_NEON)
except Exception as e:
    st.error("⚠️ La dirección de Neon no es válida. Revisa las comillas y los símbolos.")
