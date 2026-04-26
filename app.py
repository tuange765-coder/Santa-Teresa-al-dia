import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- PROCESO DE CONEXIÓN SEGURO ---
# PEGA AQUÍ TU NUEVO ENLACE DE NEON (el que tiene la clave nueva)
enlace_crudo = "postgresql://neondb_owner:AQUÍ_VA_TU_NUEVA_CLAVE@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def conectar():
    try:
        # Paso 1: Limpiar espacios
        url = enlace_crudo.strip()
        # Paso 2: Asegurar el driver correcto
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        # Paso 3: Eliminar parámetros que causan error en Streamlit
        url = url.split('&channel_binding')[0]
        
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.sidebar.error(f"❌ Error de autenticación: {e}")
        return None

engine = conectar()

if engine:
    st.sidebar.success("🚀 Conexión con Neon: ACTIVA")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

with st.sidebar:
    st.header("📻 Radio en Vivo")
    st.audio("https://stream.zeno.fm/f97vv37v908uv")
    st.divider()
    clave = st.text_input("Clave de Administrador", type="password")

tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

with tab1:
    if clave == "1966" and engine:
        st.subheader("✍️ Publicar Nueva Noticia")
        with st.form("diario", clear_on_submit=True):
            t = st.text_input("Título")
            cat = st.selectbox("Sección", ["Política", "Economía", "Sucesos", "Deportes"])
            c = st.text_area("Contenido")
            if st.form_submit_button("Publicar"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido, categoria) VALUES (:t, :c, :cat)"),
                                 {"t": t, "c": c, "cat": cat})
                    conn.commit()
                st.success("✅ Noticia guardada.")

    st.header("Últimas Noticias")
    if engine:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT titulo, contenido, categoria, fecha FROM noticias ORDER BY id DESC")).fetchall()
                for n in res:
                    with st.expander(f"{n[2]} | {n[0]}"):
                        st.write(n[1])
                        st.caption(f"Fecha: {n[3]}")
        except:
            st.info("Esperando noticias...")

with tab3:
    st.header("🎼 Espacio del Autor y Compositor")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
