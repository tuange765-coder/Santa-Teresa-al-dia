import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import base64
import io
from PIL import Image

# --- CONFIGURACION ---
st.set_page_config(page_title="Santa Teresa al Dia", layout="wide")

# --- CONEXION A BASE DE DATOS ---
try:
    if "DATABASE_URL" in st.secrets:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
    else:
        st.error("No se encontro DATABASE_URL en secrets")
        st.stop()
    
    # Probar conexion
    test = conn.query("SELECT 1", ttl=0)
    st.success("✅ Conexion a base de datos exitosa")
    
except Exception as e:
    st.error(f"Error de conexion: {e}")
    st.stop()

# --- CREAR TABLAS ---
def crear_tablas():
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
                contenido TEXT,
                fecha TEXT
            )
            """))
            
            res = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error creando tablas: {e}")
        return False

crear_tablas()

# --- CONTADOR ---
def contar_visita():
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

# --- CONTAR VISITA ---
if 'visitado' not in st.session_state:
    contar_visita()
    st.session_state.visitado = True

# --- FUNCIONES NOTICIAS ---
def publicar_noticia(titulo, contenido):
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, contenido, fecha)
                VALUES (:t, :c, :f)
            """), {"t": titulo, "c": contenido, "f": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_noticias():
    try:
        return conn.query("SELECT * FROM noticias ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png")
    st.title("Menu")
    
    # Login Admin
    es_admin = False
    if st.checkbox("Admin"):
        clave = st.text_input("Clave:", type="password")
        if clave == "1966":
            es_admin = True
            st.success("Acceso concedido")
        elif clave:
            st.error("Clave incorrecta")
    
    menu = st.radio("Ir a", ["Portada", "Noticias", "Opiniones"])

# --- ESTILOS ---
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
h1, h2, h3, p {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# --- PORTADA ---
if menu == "Portada":
    st.title("🇻🇪 Santa Teresa al Dia")
    
    col1, col2 = st.columns(2)
    with col1:
        ahora = datetime.now()
        st.metric("📅 Fecha", ahora.strftime("%d/%m/%Y"))
        st.metric("⏰ Hora", ahora.strftime("%I:%M:%S %p"))
    with col2:
        visitas = obtener_visitas()
        st.metric("👥 Visitas", f"{visitas:,}")
    
    st.markdown("---")
    st.markdown("### 📰 Ultimas Noticias")
    
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.head(3).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:200]}...")
            st.caption(f"📅 {n['fecha']}")
            st.markdown("---")
    else:
        st.info("No hay noticias. Usa el panel de admin para publicar.")

# --- NOTICIAS ---
elif menu == "Noticias":
    st.title("📰 Noticias")
    
    if es_admin:
        with st.expander("✏️ Publicar Noticia", expanded=True):
            titulo = st.text_input("Titulo")
            contenido = st.text_area("Contenido", height=200)
            if st.button("Publicar"):
                if titulo and contenido:
                    if publicar_noticia(titulo, contenido):
                        st.success("Noticia publicada!")
                        st.rerun()
                else:
                    st.warning("Completa todos los campos")
    
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.iterrows():
            st.markdown(f"### {n['titulo']}")
            st.write(n['contenido'])
            st.caption(f"📅 {n['fecha']}")
            st.markdown("---")
    else:
        st.info("No hay noticias")

# --- OPINIONES ---
elif menu == "Opiniones":
    st.title("💬 Opiniones")
    
    with st.form("opinion"):
        nombre = st.text_input("Tu nombre")
        comentario = st.text_area("Comentario")
        if st.form_submit_button("Enviar"):
            if nombre and comentario:
                st.success("Gracias por tu opinion!")
                st.balloons()
            else:
                st.warning("Completa todos los campos")
    
    st.info("⭐ Se el primero en dar tu opinion")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; padding: 20px; margin-top: 50px; background: linear-gradient(145deg, #8c6a31, #5d431a); border-radius: 15px;">
    <p style="color: #ffd700;">⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p style="color: #ffd700;">Prohibida la reproduccion - Derechos Reservados</p>
    <p style="color: #ffd700;">Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
