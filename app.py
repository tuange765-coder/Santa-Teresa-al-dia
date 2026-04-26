import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE IDENTIDAD ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN CON TU NUEVA LLAVE ---
# He usado la clave npg_OHZl6VxgNsb3 que me acabas de dar.
URL_NEON = "postgresql+psycopg2://neondb_owner:npg_OHZl6VxgNsb3@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def conectar_base_datos():
    try:
        # El strip() elimina cualquier espacio invisible que se cuele al copiar
        engine = create_engine(URL_NEON.strip())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.sidebar.error("❌ Error de acceso")
        st.sidebar.write("Revisa si la clave en Neon sigue siendo la misma.")
        return None

engine = conectar_base_datos()

if engine:
    st.sidebar.success("🚀 ¡CONEXIÓN ACTIVA!")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

# Barra Lateral
with st.sidebar:
    st.header("📻 Radio en Vivo")
    # Reproductor estable de Zeno.fm
    st.markdown('<iframe src="https://player.zeno.fm/f97vv37v908uv" width="100%" height="180" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
    st.divider()
    st.subheader("🔑 Acceso Autor")
    # Tu año de nacimiento como contraseña de la app
    clave_admin = st.text_input("Ingresa tu Clave de Administrador", type="password")

# Pestañas
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

# SECCIÓN PERIÓDICO
with tab1:
    if clave_admin == "1966" and engine:
        st.subheader("✍️ Publicar Nueva Noticia")
        with st.form("form_noticia", clear_on_submit=True):
            titulo = st.text_input("Título de la Noticia")
            contenido = st.text_area("Contenido del artículo")
            if st.form_submit_button("Publicar en el Diario"):
                try:
                    with engine.connect() as conn:
                        conn.execute(
                            text("INSERT INTO noticias (titulo, contenido) VALUES (:t, :c)"),
                            {"t": titulo, "c": contenido}
                        )
                        conn.commit()
                    st.success("✅ ¡Publicado con éxito en Neon!")
                except Exception as ex:
                    st.error("Error: Asegúrate de que la tabla 'noticias' exista en Neon.")

    st.header("Noticias Recientes")
    if engine:
        try:
            with engine.connect() as conn:
                noticias = conn.execute(text("SELECT titulo, contenido FROM noticias ORDER BY id DESC")).fetchall()
                for n in noticias:
                    with st.expander(n[0]):
                        st.write(n[1])
        except:
            st.info("El diario está listo para tu primera crónica.")

# SECCIÓN MULTIMEDIA
with tab3:
    st.header("🎼 Espacio del Autor y Compositor")
    st.subheader("🎵 Mis Composiciones")
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    st.divider()
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
