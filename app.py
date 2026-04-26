import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN CORREGIDA A NEON ---
# He usado tu nueva clave y el driver exacto para evitar el error de autenticación.
URL_FINAL = "postgresql+psycopg2://neondb_owner:npg_gbuJFqhfm3r4@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

try:
    engine = create_engine(URL_FINAL)
    # Verificamos si la puerta está abierta
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.sidebar.success("🚀 Conexión con Neon: ACTIVA")
except Exception as e:
    st.sidebar.error("❌ Error de conexión")
    st.sidebar.write(f"Nota técnica: {e}")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

# Barra Lateral
with st.sidebar:
    st.header("📻 Radio en Vivo")
    st.audio("https://stream.zeno.fm/f97vv37v908uv")
    st.divider()
    st.subheader("🔑 Acceso Administrador")
    # Usa tu año de nacimiento como clave para publicar
    clave = st.text_input("Ingresa tu Clave", type="password")

# Pestañas del Portal
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

# --- SECCIÓN 1: PERIÓDICO ---
with tab1:
    if clave == "1966":
        st.subheader("✍️ Publicar Nueva Noticia")
        with st.form("diario", clear_on_submit=True):
            titulo = st.text_input("Título de la Noticia")
            cat = st.selectbox("Sección", ["Política", "Economía", "Sucesos", "Deportes"])
            cont = st.text_area("Contenido")
            if st.form_submit_button("Publicar en el Diario"):
                try:
                    with engine.connect() as conn:
                        conn.execute(
                            text("INSERT INTO noticias (titulo, contenido, categoria) VALUES (:t, :c, :cat)"),
                            {"t": titulo, "c": cont, "cat": cat}
                        )
                        conn.commit()
                    st.success("✅ ¡Noticia guardada con éxito!")
                except Exception as ex:
                    st.error("Error: Asegúrate de que la tabla 'noticias' esté creada en Neon.")

    st.header("Últimas Noticias")
    try:
        with engine.connect() as conn:
            noticias = conn.execute(text("SELECT titulo, contenido, categoria, fecha FROM noticias ORDER BY id DESC")).fetchall()
            for n in noticias:
                with st.expander(f"{n[2]} | {n[0]}"):
                    st.write(n[1])
                    st.caption(f"Fecha: {n[3]}")
    except:
        st.info("El sistema está listo para recibir tu primera noticia.")

# --- SECCIÓN 2: VITRINA ---
with tab2:
    st.header("💎 Vitrina Comercial")
    st.write("Espacio para los emprendedores y comercios locales.")

# --- SECCIÓN 3: MULTIMEDIA ---
with tab3:
    st.header("🎼 Espacio del Autor y Compositor")
    st.subheader("🎵 Mis Composiciones")
    # Enlace de audio de ejemplo
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    st.divider()
    st.subheader("📹 Videos")
    # Enlace de video de ejemplo
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
