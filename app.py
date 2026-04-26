import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide")

# --- PEGA TU ENLACE AQUÍ ABAJO (Tal cual lo copias de Neon) ---
# Asegúrate de haberle dado al "ojo" en Neon para que se vea la clave.
ENLACE_COPIADO = "postgresql://neondb_owner:npg_gbuJFqhfm3r4@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def preparar_motor():
    try:
        url = ENLACE_COPIADO.strip()
        # Corregimos el formato para Streamlit
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        # Quitamos el pooler si está molestando
        url = url.replace("-pooler", "")
        
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Error de acceso. Revisa si la clave es correcta: {e}")
        return None

engine = preparar_motor()

if engine:
    st.sidebar.success("🚀 ¡CONEXIÓN ACTIVA!")

# --- TÍTULO ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Tu periódico y vitrina comercial en línea.")

with st.sidebar:
    st.header("📻 Radio")
    st.audio("https://stream.zeno.fm/f97vv37v908uv")
    st.divider()
    clave_autor = st.text_input("Clave (Año)", type="password")

# Pestañas
t1, t2, t3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

with t1:
    if clave_autor == "1966" and engine:
        st.subheader("✍️ Publicar Noticia")
        with st.form("form_noticia"):
            titulo = st.text_input("Título")
            contenido = st.text_area("Contenido")
            if st.form_submit_button("Subir al Diario"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido) VALUES (:t, :c)"),
                                 {"t": titulo, "c": contenido})
                    conn.commit()
                st.success("Publicado correctamente.")

with t3:
    st.header("🎼 Multimedia")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
