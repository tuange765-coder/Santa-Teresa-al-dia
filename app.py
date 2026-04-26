import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- 2. GESTIÓN DE CONEXIÓN ROBUSTA (ELIMINA EL OPERATIONALERROR) ---
def conectar_con_reintento():
    """Intenta establecer conexión y despertar a Neon si está dormido."""
    try:
        # Busca automáticamente en st.secrets
        conexion = st.connection("postgresql", type="sql")
        # Forzamos una ejecución mínima para verificar que el túnel está abierto
        with conexion.session as s:
            s.execute(text("SELECT 1"))
        return conexion
    except Exception:
        return None

# Intentamos conectar
conn = conectar_con_reintento()

# Si Neon no responde, mostramos aviso y reintentamos automáticamente
if conn is None:
    st.warning("📡 Sincronizando con la base de datos en Santa Teresa... Por favor, espera 8 segundos.")
    time.sleep(8)
    st.rerun()

# --- 3. CATEGORÍAS ---
CAT_LIST = [
    "Salud", "Laboratorios", "Opticas", "Farmacias", "Dulcerias",
    "Comida Rapida", "Panaderias", "Charcuterias", "Carnicerias",
    "Ferreterias", "Zapaterias", "Electrodomesticos", "Fibras Opticas",
    "Taxis", "Mototaxis", "Servicios", "Entes Publicos", "Otros"
]

# --- 4. INICIALIZACIÓN DE TABLAS (CON MANEJO DE ERRORES) ---
def inicializar_tablas():
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
            );
            CREATE TABLE IF NOT EXISTS opiniones (
                id SERIAL PRIMARY KEY,
                comercio_id INTEGER,
                usuario VARCHAR(100),
                comentario TEXT,
                estrellas_u INTEGER,
                fecha VARCHAR(50)
            );
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER
            );
            """))
            # Asegurar contador de visitas
            check_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not check_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            s.commit()
    except Exception:
        st.error("Error al estructurar tablas. Verifica permisos en Neon.")

inicializar_tablas()

# --- 5. TIEMPO Y ESTADÍSTICAS ---
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

# --- 6. DISEÑO VENEZOLANO (CSS CONSOLIDADO) ---
st.markdown("""
<style>
    header, footer, .stDeployButton { visibility: hidden; }
    .stApp { background-color: #0f172a; color: #ffffff; }
    .venezuela-header {
        text-align: center; padding: 40px 10px;
        background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
        border-radius: 0 0 30px 30px; margin-bottom: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }
    .stars-arc { color: #fff; font-size: 1.5em; letter-spacing: 12px; font-weight: bold; text-shadow: 2px 2px 4px #000; }
    .bronze-plaque {
        background: linear-gradient(145deg, #a67c00, #523b00); border: 4px solid #ffd700;
        padding: 40px; border-radius: 15px; text-align: center; margin-top: 50px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.8);
    }
    .bronze-text { color: #ffd700 !important; font-family: 'Georgia', serif; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 7. PANEL LATERAL ---
with st.sidebar:
    st.markdown('<h2 style="color:#ffcc00;">🇻🇪 Navegación</h2>', unsafe_allow_html=True)
    menu = st.radio("Secciones:", ["🏢 Guía Principal", "🔐 Panel Administrativo"])
    st.markdown("---")
    st.write(f"Sábado, {ahora_vzla.strftime('%d/%m/%Y')}")

# --- 8. CABECERA ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)

if menu == "🏢 Guía Principal":
    st.title("🚀 Santa Teresa al Día")
    st.info(f"📊 Total de visitas a la plataforma: {total_visitas}")
    
    busq = st.text_input("🔍 ¿Qué buscas en el Tuy?", placeholder="Ej: Panaderías, Salud...")
    
    tabs = st.tabs(["Todos"] + CAT_LIST)
    df_c = conn.query("SELECT * FROM comercios", ttl=0)

    for i, tab in enumerate(tabs):
        with tab:
            cat_nombre = (["Todos"] + CAT_LIST)[i]
            filtrado = df_c if cat_nombre == "Todos" else df_c[df_c['categoria'] == cat_nombre]
            if busq:
                filtrado = filtrado[filtrado['nombre'].str.contains(busq, case=False)]
            
            for _, r in filtrado.iterrows():
                with st.expander(f"🏢 {r['nombre']} ({r['categoria']})"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if r['foto_url']: st.image(r['foto_url'])
                    with col2:
                        st.write(f"📍 **Ubicación:** {r['ubicacion']}")
                        st.write(f"✍️ **Reseña:** {r['reseña_willian']}")
                        
                        # Formulario con Key Única para evitar duplicados
                        with st.form(key=f"form_v_{r['id']}_{i}", clear_on_submit=True):
                            u_nombre = st.text_input("Nombre")
                            u_coment = st.text_area("Opinión")
                            if st.form_submit_button("Publicar"):
                                if u_nombre and u_coment:
                                    with conn.session as s:
                                        s.execute(text("INSERT INTO opiniones (comercio_id, usuario, comentario, fecha) VALUES (:id, :u, :c, :f)"),
                                                  {"id": r['id'], "u": u_nombre, "c": u_coment, "f": ahora_vzla.strftime("%d/%m/%Y")})
                                        s.commit()
                                    st.success("¡Gracias!")
                                    time.sleep(0.5)
                                    st.rerun()

elif menu == "🔐 Panel Administrativo":
    clave = st.text_input("Contraseña:", type="password")
    if clave == "Juan*316*":
        st.success("Acceso Willian Almenar")
        # Lógica de inserción aquí

# --- 9. PLACA DE BRONCE FINAL ---
st.markdown(f"""
<div class="bronze-plaque">
    <div class="bronze-text">
        <span style="font-size: 2.2em;">Reflexiones de Willian Almenar</span><br><br>
        <span style="font-size: 1.4em; opacity: 0.9;">PROHIBIDA SU REPRODUCCIÓN</span><br>
        <span style="font-size: 1.8em; letter-spacing: 5px; display: block; margin: 15px 0;">DERECHOS RESERVADOS</span>
        <span style="font-size: 1.9em;">Santa Teresa del Tuy {ahora_vzla.year}</span>
    </div>
</div>
""", unsafe_allow_html=True)
