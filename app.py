import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN CORREGIDA A NEON ---
# He añadido +psycopg2 y eliminado el channel_binding para que no dé error
URL_FINAL = "postgresql+psycopg2://neondb_owner:npg_R8DElKfr4gtJ@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

try:
    engine = create_engine(URL_FINAL)
    # Prueba de conexión rápida
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.sidebar.success("🚀 Conexión con Neon: ACTIVA")
except Exception as e:
    st.sidebar.error("❌ Error de conexión")
    st.write(f"Error técnico: {e}")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

# Barra Lateral
with st.sidebar:
    st.header("📻 Radio en Vivo")
    st.audio("https://stream.zeno.fm/f97vv37v908uv")
    st.divider()
    clave = st.text_input("Clave de Administrador", type="password")

# Pestañas
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

# --- SECCIÓN 1: PERIÓDICO ---
with tab1:
    if clave == "1966":
        st.subheader("✍️ Publicar Nueva Noticia")
        with st.form("diario", clear_on_submit=True):
            titulo = st.text_input("Título")
            cat = st.selectbox("Sección", ["Política", "Economía", "Sucesos", "Deportes"])
            cont = st.text_area("Contenido")
            if st.form_submit_button("Enviar al Periódico"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido, categoria) VALUES (:t, :c, :cat)"),
                                 {"t": titulo, "c": cont, "cat": cat})
                    conn.commit()
                st.success("Noticia guardada en la base de datos.")

    st.header("Noticias Recientes")
    try:
        with engine.connect() as conn:
            noticias = conn.execute(text("SELECT titulo, contenido, categoria, fecha FROM noticias ORDER BY fecha DESC")).fetchall()
            for n in noticias:
                with st.expander(f"{n[2]} | {n[0]}"):
                    st.write(n[1])
                    st.caption(f"Fecha: {n[3]}")
    except:
        st.info("Aún no hay noticias para mostrar.")

# --- SECCIÓN 2: VITRINA ---
with tab2:
    st.header("💎 Vitrina Comercial")
    st.write("Espacio dedicado al comercio de Santa Teresa y Caracas.")
    # Aquí puedes añadir un formulario similar al de noticias para los comercios

# --- SECCIÓN 3: MULTIMEDIA ---
with tab3:
    st.header("🎼 Espacio del Autor y Compositor")
    st.subheader("Composiciones de Willian Almenar")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ") # Reemplaza con tu video real
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
