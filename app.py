import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN DIRECTA Y FORZADA ---
# He ajustado el enlace para saltarnos el "pooler" y entrar directo.
# Usando tu clave: npg_OHZl6VxgNsb3
URL_FINAL = "postgresql+psycopg2://neondb_owner:npg_OHZl6VxgNsb3@ep-polished-smoke-anreqn6i.us-east-1.aws.neon.tech/neondb?sslmode=require"

@st.cache_resource
def obtener_motor():
    try:
        # Creamos la conexión con un tiempo de espera más largo
        engine = create_engine(URL_FINAL.strip(), connect_args={"connect_timeout": 30})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        return e

resultado = obtener_motor()

if isinstance(resultado, Exception):
    st.sidebar.error("❌ La puerta sigue cerrada")
    st.sidebar.write(f"Aviso técnico: {resultado}")
else:
    st.sidebar.success("🚀 ¡CONEXIÓN ACTIVA!")
    engine = resultado

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música")

with st.sidebar:
    st.header("📻 Radio")
    st.markdown('<iframe src="https://player.zeno.fm/f97vv37v908uv" width="100%" height="180" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
    st.divider()
    clave_autor = st.text_input("Clave (1966)", type="password")

# Pestañas
t1, t2, t3 = st.tabs(["📰 Diario", "🛍️ Vitrina", "🎼 Multimedia"])

with t1:
    if clave_autor == "1966" and not isinstance(resultado, Exception):
        st.subheader("✍️ Publicar Noticia")
        with st.form("diario_nuevo"):
            tit = st.text_input("Título")
            cont = st.text_area("Contenido")
            if st.form_submit_button("Publicar"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido) VALUES (:t, :c)"), {"t": tit, "c": cont})
                    conn.commit()
                st.success("✅ ¡Guardado!")

    st.header("Últimas Noticias")
    if not isinstance(resultado, Exception):
        try:
            with engine.connect() as conn:
                noticias = conn.execute(text("SELECT titulo, contenido FROM noticias ORDER BY id DESC")).fetchall()
                for n in noticias:
                    with st.expander(n[0]):
                        st.write(n[1])
        except:
            st.info("Escribe tu primera noticia para estrenar el diario.")
