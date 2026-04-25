import streamlit as st
from sqlalchemy import create_engine, text

# --- CONEXIÓN CON NEON ---
# BORRA EL TEXTO DE ABAJO Y PEGA TU LLAVE DE NEON AQUÍ
DATABASE_URL = "AQUÍ_PEGA_TU_LLAVE_DE_NEON"
engine = create_engine(DATABASE_URL)

# --- INICIO DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide")

st.title("🏛️ Mi Portal: Periódico, Vitrina y Música")

# Menú lateral para la Radio
with st.sidebar:
    st.header("📻 Emisora en Vivo")
    st.audio("https://stream.zeno.fm/f97vv37v908uv") # Ejemplo de radio
    st.divider()
    clave = st.text_input("Clave de Administrador", type="password")

# Pestañas principales
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "💎 Vitrina Comercial", "🎬 Mi Música"])

with tab1:
    st.header("Noticias Diarias")
    # Si la clave es 1966 (tu año), puedes publicar
    if clave == "1966":
        with st.form("nueva_noticia"):
            titulo = st.text_input("Título de la noticia")
            seccion = st.selectbox("Sección", ["Economía", "Política", "Deportes", "Sucesos"])
            contenido = st.text_area("Contenido")
            if st.form_submit_button("Publicar Noticia"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO noticias (titulo, contenido, categoria) VALUES (:t, :c, :s)"), 
                                 {"t": titulo, "c": contenido, "s": seccion})
                    conn.commit()
                st.success("¡Noticia guardada en Neon!")

    # Mostrar noticias guardadas
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM noticias ORDER BY id DESC")).fetchall()
        for n in res:
            with st.expander(f"{n[3]} - {n[1]}"):
                st.write(n[2])

with tab2:
    st.header("🛍️ Vitrina Comercial")
    st.write("Espacio para los comercios de Caracas.")
    # Aquí iría un código similar al de noticias para guardar comercios

with tab3:
    st.header("🎵 Mi Música y Videos")
    st.subheader("Composiciones de Willian Almenar")
    st.video("https://www.youtube.com/watch?v=Ejemplo") # Aquí pondrás tus videos
