import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- 2. CONEXIÓN SEGURA A NEON CON AUTO-DESPERTAR ---
def obtener_conexion():
    try:
        # Intentamos conectar usando los Secrets de Streamlit
        conexion = st.connection("postgresql", type="sql")
        # Forzamos una consulta simple para verificar si la base de datos está activa
        with conexion.session as s:
            s.execute(text("SELECT 1"))
        return conexion
    except Exception:
        return None

# Intentamos obtener la conexión
conn = obtener_conexion()

# Si falla (Neon está dormido), esperamos y reintentamos
if conn is None:
    st.warning("⚠️ La base de datos de Santa Teresa está despertando... Por favor, espera unos segundos.")
    time.sleep(6) # Damos tiempo suficiente para que Neon arranque
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
            
            # Inicializamos contador si es la primera vez
            v_check = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not v_check:
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
        text-align: center; padding: 45px 10px;
        background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
        border-radius: 0 0 25px 25px; margin-bottom: 20px; box-shadow: 0px 10px 20px rgba(0,0,0,0.5);
    }
    .stars-arc { color: white; font-size: 1.5em; letter-spacing: 12px; font-weight: bold; text-shadow: 2px 2px 4px #000; }
    .stats-panel { background: #1f2937; padding: 15px; border-radius: 15px; border: 2px solid #ffcc00; text-align: center; }
    .bronze-plaque {
        background: linear-gradient(145deg, #8c6a31, #5d431a); border: 5px solid #d4af37;
        padding: 40px; border-radius: 15px; text-align: center; margin-top: 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.7);
    }
    .bronze-text { color: #ffd700 !important; font-family: 'Times New Roman', serif; font-weight: bold; text-shadow: 1px 1px 2px black; }
</style>
""", unsafe_allow_html=True)

# --- 7. BARRA LATERAL ---
with st.sidebar:
    st.markdown("### 🇻🇪 Opciones")
    menu = st.radio("Navegar a:", ["🏢 Guía Comercial", "🔐 Administración"])
    st.markdown("---")
    st.write(f"Viernes, {ahora_vzla.day}/{ahora_vzla.month}/{ahora_vzla.year}")

# --- 8. CABECERA VENEZOLANA ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)

if menu == "🏢 Guía Comercial":
    st.title("🚀 Santa Teresa al Día")
    st.markdown(f'<div class="stats-panel">📈 Visitas: {total_visitas}</div>', unsafe_allow_html=True)
    
    busq = st.text_input("🔍 Buscar negocio...", placeholder="¿Qué estás buscando?")
    
    tabs = st.tabs(["Todos"] + CAT_LIST)
    df_c = conn.query("SELECT * FROM comercios", ttl=0)

    for i, tab in enumerate(tabs):
        with tab:
            cat_actual = (["Todos"] + CAT_LIST)[i]
            filtrado = df_c if cat_actual == "Todos" else df_c[df_c['categoria'] == cat_actual]
            if busq:
                filtrado = filtrado[filtrado['nombre'].str.contains(busq, case=False)]
            
            for _, r in filtrado.iterrows():
                with st.expander(f"🏢 {r['nombre']}"):
                    st.write(f"📍 {r['ubicacion']}")
                    st.info(f"✍️ {r['reseña_willian']}")
                    
                    # Formulario de Opiniones corregido para evitar duplicados
                    with st.form(key=f"form_op_{r['id']}_{i}", clear_on_submit=True):
                        u_name = st.text_input("Tu Nombre")
                        u_comm = st.text_area("Tu Opinión")
                        if st.form_submit_button("Enviar Opinión"):
                            if u_name and u_comm:
                                with conn.session as s:
                                    s.execute(text("INSERT INTO opiniones (comercio_id, usuario, comentario, fecha) VALUES (:id, :u, :c, :f)"),
                                              {"id": r['id'], "u": u_name, "c": u_comm, "f": ahora_vzla.strftime("%d/%m/%Y")})
                                    s.commit()
                                st.success("¡Gracias por tu aporte!")
                                time.sleep(0.5)
                                st.rerun()

elif menu == "🔐 Administración":
    clave = st.text_input("Contraseña Maestra", type="password")
    if clave == "Juan*316*":
        st.success("Acceso concedido, Willian.")
        # Aquí puedes colocar el formulario para agregar comercios que tenías anteriormente

# --- 9. PLACA DE BRONCE FINAL ---
st.markdown(f"""
<div class="bronze-plaque">
    <div class="bronze-text">
        <span style="font-size: 2.2em;">Reflexiones de Willian Almenar</span><br><br>
        <span style="font-size: 1.5em; opacity: 0.85;">Prohibida la reproducción total o parcial</span><br>
        <span style="font-size: 1.8em; letter-spacing: 6px; display: block; margin: 15px 0;">DERECHOS RESERVADOS</span>
        <span style="font-size: 1.9em;">Santa Teresa del Tuy {ahora_vzla.year}</span>
    </div>
</div>
""", unsafe_allow_html=True)
