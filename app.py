import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import io
import random

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide"
)

# --- CONEXION A BASE DE DATOS ---
@st.cache_resource
def init_connection():
    try:
        if "DATABASE_URL" in st.secrets:
            conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
            return conn
        else:
            st.error("No se encontró configuración de base de datos")
            st.stop()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

conn = init_connection()

# --- CREACION DE TABLAS ---
def create_tables():
    try:
        with conn.session as s:
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 0
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                categoria TEXT,
                contenido TEXT,
                fecha TEXT
            )
            """))
            
            res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            s.commit()
    except Exception as e:
        st.error(f"Error creando tablas: {e}")

create_tables()

# --- CONTADOR DE VISITAS ---
def actualizar_visitas():
    try:
        with conn.session as s:
            s.execute(text("UPDATE visitas SET conteo = conteo + 1 WHERE id = 1"))
            s.commit()
    except:
        pass

def obtener_visitas():
    try:
        res = conn.query("SELECT conteo FROM visitas WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 0
    except:
        return 0

# --- ACTUALIZAR CONTADOR ---
if 'visitado' not in st.session_state:
    actualizar_visitas()
    st.session_state.visitado = True

# --- LOGIN ADMIN ---
CLAVE_ADMIN = "1966"
es_admin = False

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
    st.title("📋 Menú")
    
    if st.checkbox("🔐 Admin"):
        clave = st.text_input("Clave:", type="password")
        if clave == CLAVE_ADMIN:
            es_admin = True
            st.success("Acceso concedido")
        elif clave:
            st.error("Clave incorrecta")
    
    menu = st.radio("Navegar", [
        "🏠 Portada",
        "📰 Noticias",
        "🙏 Reflexiones",
        "⚠️ Denuncias",
        "💬 Opiniones"
    ])

# --- FUNCIONES CRUD ---
def publicar_noticia(titulo, categoria, contenido):
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, fecha)
                VALUES (:t, :c, :cont, :f)
            """), {"t": titulo, "c": categoria, "cont": contenido, "f": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_noticias():
    try:
        return conn.query("SELECT * FROM noticias ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

# --- ESTILOS CSS ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%);
}
.main > div {
    background-color: rgba(0,0,0,0.7);
    border-radius: 15px;
    padding: 20px;
}
h1, h2, h3, p, span {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# --- PORTADA ---
if menu == "🏠 Portada":
    st.title("🇻🇪 Santa Teresa al Día")
    
    col1, col2 = st.columns(2)
    with col1:
        ahora = datetime.now()
        st.metric("📅 Fecha", ahora.strftime("%d/%m/%Y"))
        st.metric("⏰ Hora", ahora.strftime("%I:%M:%S %p"))
    
    with col2:
        visitas = obtener_visitas()
        st.metric("👥 Visitas", f"{visitas:,}")
    
    st.markdown("---")
    st.markdown("### 📰 Últimas Noticias")
    
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.head(3).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:200]}...")
            st.caption(f"📅 {n['fecha']} | 🏷️ {n['categoria']}")
            st.markdown("---")
    else:
        st.info("No hay noticias aún. El administrador puede publicar.")

# --- NOTICIAS ---
elif menu == "📰 Noticias":
    st.title("📰 Noticias")
    
    if es_admin:
        with st.expander("✏️ Publicar Noticia", expanded=True):
            titulo = st.text_input("Título")
            categoria = st.selectbox("Categoría", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=200)
            
            if st.button("📢 Publicar"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido):
                        st.success("¡Noticia publicada!")
                        st.rerun()
                    else:
                        st.error("Error al publicar")
                else:
                    st.warning("Completa todos los campos")
    
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.iterrows():
            with st.container():
                st.markdown(f"### {n['titulo']}")
                st.caption(f"🏷️ {n['categoria']} | 📅 {n['fecha']}")
                st.write(n['contenido'])
                st.markdown("---")
    else:
        st.info("No hay noticias publicadas")

# --- REFLEXIONES ---
elif menu == "🙏 Reflexiones":
    st.title("🙏 Pan de Vida y Reflexiones")
    
    if es_admin:
        with st.form("nueva_reflexion"):
            titulo = st.text_input("Título", value=f"Reflexión del {datetime.now().strftime('%d/%m/%Y')}")
            contenido = st.text_area("Mensaje", height=150)
            if st.form_submit_button("💾 Guardar"):
                if titulo and contenido:
                    st.success("Reflexión guardada")
                else:
                    st.warning("Completa los campos")
    
    st.info("📖 *La palabra de hoy trae paz y esperanza a nuestra comunidad*")
    st.markdown("> *Bienaventurados los pacificadores, porque ellos serán llamados hijos de Dios*")
    st.caption("— Mateo 5:9")

# --- DENUNCIAS ---
elif menu == "⚠️ Denuncias":
    st.title("⚠️ Denuncias Ciudadanas")
    
    with st.form("denuncia_form"):
        nombre = st.text_input("Tu nombre (opcional)", placeholder="Anónimo")
        titulo = st.text_input("Título de la denuncia")
        descripcion = st.text_area("Descripción", height=150)
        ubicacion = st.text_input("Ubicación")
        
        if st.form_submit_button("🚨 Enviar Denuncia"):
            if titulo and descripcion:
                st.success("✅ Denuncia recibida. Las autoridades la revisarán.")
                st.balloons()
            else:
                st.warning("Título y descripción son obligatorios")

# --- OPINIONES ---
elif menu == "💬 Opiniones":
    st.title("💬 Opiniones")
    
    with st.form("opinion_form"):
        nombre = st.text_input("Tu nombre")
        comentario = st.text_area("Tu opinión", height=100)
        estrellas = st.slider("Calificación", 1, 5, 5)
        
        if st.form_submit_button("Enviar Opinión"):
            if nombre and comentario:
                st.success("¡Gracias por tu opinión!")
                st.balloons()
            else:
                st.warning("Completa todos los campos")
    
    st.markdown("---")
    st.markdown("### Opiniones de la comunidad")
    st.info("⭐ Sé el primero en dar tu opinión")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; padding: 30px; margin-top: 50px; background: linear-gradient(145deg, #8c6a31, #5d431a); border-radius: 15px; border: 3px solid #d4af37;">
    <p style="color: #ffd700; font-size: 1.2em;">⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p style="color: #ffd700;">Prohibida la reproducción total o parcial - Derechos Reservados</p>
    <p style="color: #ffd700;">Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
