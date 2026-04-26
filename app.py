import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- 2. CONEXIÓN SEGURA A NEON (POSTGRESQL) ---
# Se utiliza st.connection para leer directamente de los Secrets
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("⚠️ Error de conexión. Verifica los Secrets en Streamlit Cloud.")
    st.stop()

# --- 3. CATEGORÍAS ---
CAT_LIST = [
    "Salud", "Laboratorios", "Opticas", "Farmacias", "Dulcerias",
    "Comida Rapida", "Panaderias", "Charcuterias", "Carnicerias",
    "Ferreterias", "Zapaterias", "Electrodomesticos", "Fibras Opticas",
    "Taxis", "Mototaxis", "Servicios", "Entes Publicos", "Otros"
]

# --- 4. INICIALIZACIÓN DE TABLAS (DENTRO DE UN BLOQUE DE SEGURIDAD) ---
def inicializar_base_de_datos():
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
            s.execute(text("CREATE TABLE IF NOT EXISTS fotos_comercios (id SERIAL PRIMARY KEY, comercio_id INTEGER, foto_data TEXT)"))
            s.execute(text("CREATE TABLE IF NOT EXISTS opiniones (id SERIAL PRIMARY KEY, comercio_id INTEGER, usuario VARCHAR(100), comentario TEXT, estrellas_u INTEGER, fecha VARCHAR(50))"))
            s.execute(text("CREATE TABLE IF NOT EXISTS visitas (id INTEGER PRIMARY KEY, conteo INTEGER)"))
            s.execute(text("CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, logo_data TEXT)"))
            
            # Inicializar contador de visitas si no existe
            res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            s.commit()
    except Exception:
        # Si Neon está en reposo, esperamos un poco
        time.sleep(2)

inicializar_base_de_datos()

# --- 5. LÓGICA DE VISITAS Y TIEMPO ---
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
        text-align: center; padding: 50px 10px;
        background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
        border-radius: 0 0 30px 30px; margin-bottom: 25px; box-shadow: 0px 8px 15px rgba(0,0,0,0.5);
    }
    .stars-arc { color: white; font-size: 1.5em; letter-spacing: 10px; font-weight: bold; text-shadow: 2px 2px 4px #000; }
    .stats-panel { background: #1f2937; padding: 15px; border-radius: 15px; border: 2px solid #ffcc00; text-align: center; }
    .bronze-plaque {
        background: linear-gradient(145deg, #8c6a31, #5d431a); border: 4px solid #d4af37;
        padding: 40px; border-radius: 15px; text-align: center; margin-top: 50px;
    }
    .bronze-text { color: #ffd700 !important; font-family: 'Times New Roman', serif; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 7. PANEL LATERAL ---
with st.sidebar:
    st.markdown('<h1 style="color:#ffcc00;">🇻🇪 Menú</h1>', unsafe_allow_html=True)
    opcion = st.radio("Ir a:", ["🏢 Guía Comercial", "🔐 Administración"])
    st.markdown("---")
    st.info("Autor: Willian Almenar\nSanta Teresa del Tuy")

# --- 8. ENCABEZADO ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)

# --- 9. INTERFAZ PÚBLICA ---
if opcion == "🏢 Guía Comercial":
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        st.title("🚀 Santa Teresa al Día")
    with col_v2:
        st.markdown(f'<div class="stats-panel"><b>VISITAS TOTALES: {total_visitas}</b></div>', unsafe_allow_html=True)

    busqueda = st.text_input("🔍 Buscar negocio o categoría...", placeholder="Ej: Panadería...")
    
    tabs = st.tabs(["Todos"] + CAT_LIST)
    df_comercios = conn.query("SELECT * FROM comercios", ttl=0)

    for i, tab in enumerate(tabs):
        with tab:
            categoria_seleccionada = (["Todos"] + CAT_LIST)[i]
            
            # Filtrado de datos
            filtrado = df_comercios
            if categoria_seleccionada != "Todos":
                filtrado = filtrado[filtrado['categoria'] == categoria_seleccionada]
            if busqueda:
                filtrado = filtrado[filtrado['nombre'].str.contains(busqueda, case=False)]
            
            if filtrado.empty:
                st.write("No se encontraron resultados.")
            else:
                for _, r in filtrado.iterrows():
                    with st.expander(f"🏢 {r['nombre']} - {r['categoria']}"):
                        c_img, c_info = st.columns([1, 2])
                        with c_img:
                            if r['foto_url']: st.image(r['foto_url'])
                        with c_info:
                            st.write(f"📍 **Ubicación:** {r['ubicacion']}")
                            st.write(f"⭐ **Calificación:** {'⭐' * int(r['estrellas_w'] if r['estrellas_w'] else 0)}")
                            st.info(f"✍️ **Reseña:** {r['reseña_willian']}")
                            if r['maps_url']: st.link_button("Ver en Google Maps", r['maps_url'])
                            
                            # --- SECCIÓN OPINIONES (CON KEYS ÚNICAS) ---
                            st.markdown("---")
                            st.write("### Dejar Opinión")
                            # La clave incluye el ID y la pestaña para evitar el error de duplicados
                            with st.form(key=f"form_op_{r['id']}_{i}", clear_on_submit=True):
                                nombre_u = st.text_input("Nombre")
                                coment_u = st.text_area("Comentario")
                                if st.form_submit_button("Enviar"):
                                    if nombre_u and coment_u:
                                        with conn.session as s:
                                            s.execute(text("INSERT INTO opiniones (comercio_id, usuario, comentario, fecha) VALUES (:id, :u, :c, :f)"),
                                                      {"id": r['id'], "u": nombre_u, "c": coment_u, "f": ahora_vzla.strftime("%d/%m/%Y")})
                                            s.commit()
                                        st.success("¡Opinión enviada!")
                                        time.sleep(0.5)
                                        st.rerun()

# --- 10. ADMINISTRACIÓN ---
elif opcion == "🔐 Administración":
    password = st.text_input("Clave Maestra:", type="password")
    if password == "Juan*316*":
        st.success("Bienvenido Willian")
        # Aquí puedes añadir el formulario de "Agregar Comercio" que ya tenías
        with st.expander("➕ Agregar Nuevo Comercio"):
            with st.form("add_com"):
                n_nom = st.text_input("Nombre")
                n_cat = st.selectbox("Categoría", CAT_LIST)
                n_ub = st.text_input("Ubicación")
                n_res = st.text_area("Tu Reseña")
                n_est = st.slider("Estrellas", 1, 5, 5)
                if st.form_submit_button("Guardar"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO comercios (nombre, categoria, ubicacion, reseña_willian, estrellas_w) VALUES (:n, :c, :u, :r, :e)"),
                                  {"n": n_nom, "c": n_cat, "u": n_ub, "r": n_res, "e": n_est})
                        s.commit()
                    st.success("Guardado con éxito.")
                    st.rerun()

# --- 11. PLACA DE BRONCE FINAL ---
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
