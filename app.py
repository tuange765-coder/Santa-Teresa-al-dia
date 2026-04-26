import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN DIRECTA (SIN POOLER) ---
# He quitado la palabra "-pooler" del enlace para evitar el error de autenticación.
URL_NEON = "postgresql+psycopg2://neondb_owner:npg_5iCVFAvc6SIZ@ep-polished-smoke-anreqn6i.us-east-1.aws.neon.tech/neondb?sslmode=require"

def conectar():
    try:
        # Usamos la conexión directa que es más estable
        engine = create_engine(URL_NEON.strip(), connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.sidebar.error("❌ La llave aún no abre la puerta.")
        st.sidebar.write("Detalle técnico:", str(e))
        return None

engine = conectar()

if engine:
    st.sidebar.success("🚀 ¡CONEXIÓN ACTIVA!")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

with st.sidebar:
    st.header("📻 Radio en Vivo")
    st.audio("https://stream.zeno.fm/f97vv37v908uv")
    st.divider()
    st.subheader("🔑 Acceso Autor")
    clave = st.text_input("Ingresa tu Clave (1966)", type="password")

# Pestañas
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

# SECCIÓN PERIÓDICO
with tab1:
    if clave == "1966" and engine:
        st.subheader("✍️ Publicar Nueva Noticia")
        with st.form("form_noticia", clear_on_submit=True):
            titulo = st.text_input("Título")
            seccion = st.selectbox("Sección", ["Política", "Economía", "Sucesos", "Deportes"])
            contenido = st.text_area("Contenido")
            if st.form_submit_button("Publicar"):
                try:
                    with engine.connect() as conn:
                        conn.execute(
                            text("INSERT INTO noticias (titulo, contenido, categoria) VALUES (:t, :c, :s)"),
                            {"t": titulo, "c": contenido, "s": seccion}
                        )
                        conn.commit()
                    st.success("✅ ¡Noticia guardada!")
                except Exception as ex:
                    st.error("Error al guardar. Verifica que la tabla existe en Neon.")

    st.header("Últimas Noticias")
    if engine:
        try:
            with engine.connect() as conn:
                noticias = conn.execute(text("SELECT titulo, contenido, categoria, fecha FROM noticias ORDER BY id DESC")).fetchall()
                for n in noticias:
                    with st.expander(f"{n[2]} | {n[0]}"):
                        st.write(n[1])
                        st.caption(f"Fecha: {n[3]}")
        except:
            st.info("Sistema listo. Publica tu primera noticia.")

# SECCIÓN MULTIMEDIA
with tab3:
    st.header("🎼 Multimedia")
    st.subheader("🎵 Mis Composiciones")
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    st.divider()
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
