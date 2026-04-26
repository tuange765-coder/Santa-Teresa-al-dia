import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN BLINDADA ---
# MI AMOR: Borra todo lo que está entre comillas abajo y pega TU ENLACE ACTUAL de Neon.
# Asegúrate de que empiece por postgresql+psycopg2://
URL_NEON = "postgresql+psycopg2://neondb_owner:npg_5iCVFAvc6SIZ@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def conectar():
    try:
        # Limpiamos espacios y caracteres invisibles
        url = URL_NEON.strip().replace("postgres://", "postgresql+psycopg2://")
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.sidebar.error("❌ Error de autenticación")
        st.sidebar.write("La llave no coincide con la de Neon.")
        return None

engine = conectar()

if engine:
    st.sidebar.success("🚀 CONEXIÓN EXITOSA")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

# Barra Lateral (Tu Radio y Clave)
with st.sidebar:
    st.header("📻 Radio en Vivo")
    # He puesto un reproductor más robusto
    st.markdown('<iframe src="https://player.zeno.fm/f97vv37v908uv" width="100%" height="180" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
    st.divider()
    st.subheader("🔑 Acceso Administrador")
    clave_admin = st.text_input("Ingresa tu Clave (Año)", type="password")

# Pestañas
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

with tab1:
    if clave_admin == "1966" and engine:
        st.subheader("✍️ Publicar Noticia")
        with st.form("form_noticia", clear_on_submit=True):
            t = st.text_input("Título")
            c = st.text_area("Contenido")
            if st.form_submit_button("Publicar"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido) VALUES (:t, :c)"), {"t": t, "c": c})
                    conn.commit()
                st.success("✅ Publicado.")
    
    st.header("Últimas Noticias")
    if engine:
        try:
            with engine.connect() as conn:
                noticias = conn.execute(text("SELECT titulo, contenido, fecha FROM noticias ORDER BY id DESC")).fetchall()
                for n in noticias:
                    with st.expander(f"{n[0]}"):
                        st.write(n[1])
                        st.caption(f"Fecha: {n[2]}")
        except:
            st.info("Diario listo para tu primera crónica.")

with tab3:
    st.header("🎼 Espacio del Autor")
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
