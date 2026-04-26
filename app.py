import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Portal Willian Almenar", layout="wide", page_icon="🏛️")

# --- CONEXIÓN DEFINITIVA A NEON ---
# He integrado tu usuario y clave, ajustando el driver para que Python lo reconozca.
URL_FINAL = "postgresql+psycopg2://neondb_owner:npg_R8DElKfr4gtJ@ep-polished-smoke-anreqn6i-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

try:
    # Creamos el motor de conexión con la llave que me diste
    engine = create_engine(URL_FINAL)
    # Prueba de conexión rápida al iniciar
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.sidebar.success("🚀 Conexión con Neon: ACTIVA")
except Exception as e:
    st.sidebar.error("❌ Error de conexión")
    st.sidebar.write(f"Ajuste técnico: {e}")

# --- DISEÑO DEL PORTAL ---
st.title("🏛️ Portal Integral: Willian Almenar")
st.write("Periódico Diario • Vitrina Comercial • Música y Video")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📻 Radio en Vivo")
    # Emisora de ejemplo (puedes cambiar el link luego)
    st.audio("https://stream.zeno.fm/f97vv37v908uv")
    st.divider()
    st.subheader("🔑 Panel de Autor")
    # Tu clave de acceso basada en tu año de nacimiento
    clave = st.text_input("Clave de Administrador", type="password")

# --- PESTAÑAS DEL PORTAL ---
tab1, tab2, tab3 = st.tabs(["📰 Periódico", "🛍️ Vitrina", "🎼 Multimedia"])

# --- SECCIÓN 1: PERIÓDICO (DIARIO) ---
with tab1:
    if clave == "1966":
        st.subheader("✍️ Redactar Noticia para el Diario")
        with st.form("diario_form", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                titulo = st.text_input("Título de la Noticia")
            with col2:
                cat = st.selectbox("Sección", ["Política", "Economía", "Sucesos", "Deportes", "Cultura"])
            
            cont = st.text_area("Desarrollo de la noticia", height=150)
            
            if st.form_submit_button("Publicar Noticia"):
                if titulo and cont:
                    try:
                        with engine.connect() as conn:
                            conn.execute(
                                text("INSERT INTO noticias (titulo, contenido, categoria) VALUES (:t, :c, :cat)"),
                                {"t": titulo, "c": cont, "cat": cat}
                            )
                            conn.commit()
                        st.success("✅ Noticia guardada en Neon y publicada.")
                    except Exception as ex:
                        st.error(f"Error al guardar: {ex}")
                else:
                    st.warning("Por favor, completa el título y el contenido.")

    st.header("Noticias Recientes")
    try:
        with engine.connect() as conn:
            # Buscamos las noticias en tu base de datos
            noticias = conn.execute(text("SELECT titulo, contenido, categoria, fecha FROM noticias ORDER BY fecha DESC")).fetchall()
            if noticias:
                for n in noticias:
                    with st.expander(f"{n[2]} | {n[0]}"):
                        st.write(n[1])
                        st.caption(f"Publicado el: {n[3]}")
            else:
                st.info("El diario está listo. Usa tu clave para publicar la primera noticia.")
    except:
        st.info("Iniciando sistema de noticias...")

# --- SECCIÓN 2: VITRINA COMERCIAL ---
with tab2:
    st.header("💎 Vitrina Comercial")
    st.write("Espacio para los comercios de Santa Teresa del Tuy y Caracas.")
    st.info("Próximamente: Registra tu negocio aquí.")

# --- SECCIÓN 3: MULTIMEDIA ---
with tab3:
    st.header("🎼 Espacio del Autor y Compositor")
    st.subheader("🎵 Mis Composiciones")
    # Aquí puedes colocar tus enlaces reales de audio
    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    st.caption("Obra original de Willian Almenar")
    
    st.divider()
    st.subheader("📹 Videos")
    # Reemplaza este link con tu video de YouTube cuando lo tengas
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
