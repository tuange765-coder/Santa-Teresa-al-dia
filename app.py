import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide")

# --- PASO ÚNICO: PEGA TU ENLACE AQUÍ ---
# Dale al "ojo" en Neon, copia el enlace y pégalo entre las comillas de abajo:
ENLACE_NEON = "postgresql://neondb_owner:npg_5iCVFAvc6SIZ@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def conectar_sistema():
    try:
        # El código limpia el enlace automáticamente por ti
        url = ENLACE_NEON.strip().replace("postgresql://", "postgresql+psycopg2://")
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.sidebar.error("❌ La llave no abre la puerta todavía.")
        return None

engine = conectar_sistema()

if engine:
    st.sidebar.success("🚀 ¡CONEXIÓN EXITOSA!")

# --- INTERFAZ DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Tu periódico diario y vitrina comercial.")

with st.sidebar:
    st.header("📻 Radio")
    st.markdown('<iframe src="https://player.zeno.fm/f97vv37v908uv" width="100%" height="180" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
    st.divider()
    clave_acceso = st.text_input("Clave de Autor (1966)", type="password")

# Pestañas
t1, t2, t3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

with t1:
    if clave_acceso == "1966" and engine:
        st.subheader("✍️ Publicar Noticia")
        with st.form("nuevo_post"):
            titulo = st.text_input("Título")
            texto = st.text_area("Contenido")
            if st.form_submit_button("Subir Noticia"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido) VALUES (:t, :c)"), {"t": titulo, "c": texto})
                    conn.commit()
                st.success("✅ Publicado en el diario.")

with t3:
    st.header("🎼 Multimedia")
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
