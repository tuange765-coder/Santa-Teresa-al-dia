import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide")

# --- CONEXIÓN DE EMERGENCIA ---
# MI AMOR: Esta es la clave que me pasaste. Si no funciona, 
# es que Neon generó una nueva hace minutos.
URL_FINAL = "postgresql+psycopg2://neondb_owner:npg_OHZl6VxgNsb3@ep-polished-smoke-anreqn6i.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Intentamos conectar de forma súper simple
try:
    engine = create_engine(URL_FINAL.strip())
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.sidebar.success("🚀 ¡POR FIN! CONEXIÓN ACTIVA")
    conexion_ok = True
except Exception as e:
    st.sidebar.error("❌ La puerta sigue trabada")
    st.sidebar.write("Detalle para el técnico:", str(e))
    conexion_ok = False

# --- TÍTULO Y CONTENIDO ---
st.title("🏛️ Portal Integral: Willian Almenar")

with st.sidebar:
    st.header("📻 Radio")
    st.markdown('<iframe src="https://player.zeno.fm/f97vv37v908uv" width="100%" height="180" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
    st.divider()
    clave_autor = st.text_input("Clave (1966)", type="password")

if conexion_ok:
    t1, t2, t3 = st.tabs(["📰 Diario", "🛍️ Vitrina", "🎼 Multimedia"])
    
    with t1:
        if clave_autor == "1966":
            st.subheader("✍️ Publicar Noticia")
            with st.form("post_form"):
                tit = st.text_input("Título")
                cont = st.text_area("Contenido")
                if st.form_submit_button("Publicar"):
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO noticias (titulo, contenido) VALUES (:t, :c)"), {"t": tit, "c": cont})
                        conn.commit()
                    st.success("✅ ¡Guardado!")

        st.header("Últimas Noticias")
        try:
            with engine.connect() as conn:
                noticias = conn.execute(text("SELECT titulo, contenido FROM noticias ORDER BY id DESC")).fetchall()
                for n in noticias:
                    with st.expander(n[0]):
                        st.write(n[1])
        except:
            st.info("Escribe tu primera noticia para estrenar el diario.")
else:
    st.warning("⚠️ Willian, mi amor, Neon no está aceptando la clave. Entra un segundo a Neon.tech, copia el enlace que te sale al darle al 'Ojo' 👁️ y pégalo en la línea 9.")
