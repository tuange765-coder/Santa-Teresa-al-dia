import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- 2. CONEXIÓN SEGURA A NEON CON REINTENTOS ---
def get_connection():
    try:
        # Esto busca automáticamente los Secrets configurados en Streamlit Cloud
        connection = st.connection("postgresql", type="sql")
        # Prueba de vida: intentamos una consulta simple para despertar a Neon
        with connection.session as s:
            s.execute(text("SELECT 1"))
        return connection
    except Exception:
        return None

conn = get_connection()

# Si la conexión falla, mostramos un aviso amigable y reintentamos
if conn is None:
    st.warning("⚠️ La base de datos de Santa Teresa está despertando... Por favor, espera 5 segundos.")
    time.sleep(5)
    st.rerun()

# --- 3. CATEGORÍAS ---
CAT_LIST = [
    "Salud", "Laboratorios", "Opticas", "Farmacias", "Dulcerias",
    "Comida Rapida", "Panaderias", "Charcuterias", "Carnicerias",
    "Ferreterias", "Zapaterias", "Electrodomesticos", "Fibras Opticas",
    "Taxis", "Mototaxis", "Servicios", "Entes Publicos", "Otros"
]

# --- 4. INICIALIZACIÓN DE TABLAS ---
def init_db():
    try:
        with conn.session as s:
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS comercios (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255),
                categoria VARCHAR(100),
                ubicacion TEXT,
                foto_url TEXT,
                reseña_willian TEXT,
                estrellas_w INTEGER,
                maps_url TEXT,
                visitas INTEGER DEFAULT 0
            )"""))
            s.execute(text("CREATE TABLE IF NOT EXISTS opiniones (id SERIAL PRIMARY KEY, comercio_id INTEGER, usuario VARCHAR(100), comentario TEXT, estrellas_u INTEGER, fecha VARCHAR(50))"))
            s.execute(text("CREATE TABLE IF NOT EXISTS visitas (id INTEGER PRIMARY KEY, conteo INTEGER)"))
            
            res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            s.commit()
    except Exception:
        pass

init_db()

# --- 5. LÓGICA DE TIEMPO Y VISITAS ---
ahora_vzla = datetime.utcnow() - timedelta(hours=4)

if 'visitado' not in st.session_state:
    try:
        with conn.session as s:
            s.execute(text("UPDATE visitas SET conteo = conteo + 1 WHERE id = 1"))
            s.commit()
        st.session_state.visitado = True
    except Exception:
        pass

res_visitas = conn.query("SELECT conteo FROM visitas WHERE id = 1", ttl=0)
total_visitas = res_visitas.iloc[0,0] if not res_visitas.empty else 0

# --- 6. ESTILOS CSS (DISEÑO VENEZUELA) ---
st.markdown("""
<style>
    header, footer, .stDeployButton { visibility: hidden; }
    .stApp { background-color: #111827; color: #ffffff; }
    .venezuela-header {
        text-align: center; padding: 40px 10px;
        background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
        border-radius: 0 0 25px 25px; margin-bottom: 20px;
    }
    .stars-arc { color: white; font-size: 1.5em; letter-spacing: 8px; font-weight: bold; text-shadow: 2px 2px 4px #000; }
    .stats-panel { background: #1f2937; padding: 15px; border-radius: 15px; border: 2px solid #ffcc00; text-align: center; }
    .bronze-plaque {
        background: linear-gradient(145deg, #8c6a31, #5d431a); border: 4px solid #d4af37;
        padding: 30px; border-radius: 15px; text-align: center; margin-top: 40px;
    }
    .bronze-text { color: #ffd700 !important; font-family: serif; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 7. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("### 🇻🇪 Opciones")
    menu = st.radio("Sección:", ["🏢 Ver Guía", "🔐 Panel Maestro"])
    st.markdown("---")
    st.write(f"Viernes, {ahora_vzla.day}/{ahora_vzla.month}/{ahora_vzla.year}")

# --- 8. ENCABEZADO ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)

if menu == "🏢 Ver Guía":
    st.title("🚀 Santa Teresa al Día")
    st.markdown(f'<div class="stats-panel">Visitas: {total_visitas}</div>', unsafe_allow_html=True)
    
    busq = st.text_input("🔍 Buscar...", placeholder="¿Qué necesitas hoy?")
    
    tabs = st.tabs(["Todos"] + CAT_LIST)
    df = conn.query("SELECT * FROM comercios", ttl=0)

    for i, tab in enumerate(tabs):
        with tab:
            cat_actual = (["Todos"] + CAT_LIST)[i]
            filtrado = df if cat_actual == "Todos" else df[df['categoria'] == cat_actual]
            if busq:
                filtrado = filtrado[filtrado['nombre'].str.contains(busq, case=False)]
            
            for _, r in filtrado.iterrows():
                with st.expander(f"🏢 {r['nombre']}"):
                    st.write(f"📍 {r['ubicacion']}")
                    st.info(f"✍️ {r['reseña_willian']}")
                    
                    # Formulario de Opiniones con Key única para evitar errores de duplicados
                    with st.form(key=f"op_{r['id']}_{i}", clear_on_submit=True):
                        user = st.text_input("Nombre")
                        comm = st.text_area("Comentario")
                        if st.form_submit_button("Enviar"):
                            if user and comm:
                                with conn.session as s:
                                    s.execute(text("INSERT INTO opiniones (comercio_id, usuario, comentario, fecha) VALUES (:id, :u, :c, :f)"),
                                              {"id": r['id'], "u": user, "c": comm, "f": ahora_vzla.strftime("%d/%m/%Y")})
                                    s.commit()
                                st.success("¡Gracias!")
                                time.sleep(0.5)
                                st.rerun()

elif menu == "🔐 Panel Maestro":
    pwd = st.text_input("Contraseña", type="password")
    if pwd == "Juan*316*":
        st.success("Acceso autorizado")
        # Aquí puedes colocar tu código para agregar comercios

# --- 9. PLACA DE BRONCE ---
st.markdown(f"""
<div class="bronze-plaque">
    <div class="bronze-text">
        <span style="font-size: 2em;">Reflexiones de Willian Almenar</span><br>
        <span style="font-size: 1.5em; letter-spacing: 5px;">DERECHOS RESERVADOS</span><br>
        <span style="font-size: 1.8em;">Santa Teresa del Tuy {ahora_vzla.year}</span>
    </div>
</div>
""", unsafe_allow_html=True)
