import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from PIL import Image, ImageFile
import base64
import urllib.parse

# --- FUNCIÓN PARA MÚSICA DE FONDO ---
def autoplay_music(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f"""
                <audio autoplay loop>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
            st.markdown(md, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- ACTIVAR MÚSICA ---
# Cambia "mi_musica.mp3" por el nombre exacto de tu canción en GitHub
autoplay_music("mi_musica.mp3")

# --- ESTILO VENEZUELA (TU DISEÑO ORIGINAL) ---
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.viewerBadge_container__1QSob {display: none !important;}
.stDeployButton {display: none !important;}
.stAppToolbar {visibility: hidden !important; display: none !important;}
[data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
button[title="Manage app"] {display: none !important;}
div[data-testid="stStatusWidget"] {display: none !important;}
.stAppDeployButton {display: none !important;}

.stApp { background-color: #111827; color: #ffffff; }

/* REFUERZO DE COLOR PARA LETRAS Y PESTAÑAS */
h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
    color: #ffffff !important;
}

/* Estilo para las pestañas (Tabs) para que se vean claras */
button[data-baseweb="tab"] p {
    color: #ffcc00 !important;
    font-weight: bold !important;
    font-size: 1.1em !important;
}

.venezuela-header {
    text-align: center;
    padding: 60px 10px 40px 10px;
    background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
    border-radius: 100% 100% 25px 25px / 120% 120% 25px 25px;
    margin-bottom: 30px;
    box-shadow: 0px 10px 20px rgba(0,0,0,0.6);
}
.stars-arc {
    color: white;
    font-size: 2.5em;
    letter-spacing: 15px;
    font-weight: bold;
    text-shadow: 3px 3px 6px #000;
    margin-top: -15px;
}

.logo-container {
    text-align: center;
    margin-top: -50px; /* Ajustado para el nuevo tamaño del logo */
    margin-bottom: 20px;
}
.app-logo {
    border-radius: 50% / 30%;
    border: 3px solid #ffcc00;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.5);
}

input, textarea, [data-baseweb="select"] {
    background-color: #ffffff !important;
    color: #000000 !important;
    font-weight: bold !important;
}

.footer-willian {
    background: #000;
    color: #fff;
    padding: 30px;
    text-align: center;
    border-top: 4px solid #ffcc00;
    margin-top: 50px;
}
.gold-text {
    background: linear-gradient(to bottom, #cf9710 22%, #ffcc00 24%, #f1c40f 26%, #fff700 27%, #ffcc00 40%, #e1aa33 78%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: bold;
    font-size: 1.2em;
}

.maps-button {
    display: inline-block;
    padding: 10px 20px;
    background-color: #ea4335;
    color: white !important;
    text-decoration: none;
    border-radius: 5px;
    font-weight: bold;
    margin-top: 10px;
    text-align: center;
}

/* Estilo para que la barra lateral combine con tu diseño */
[data-testid="stSidebar"] {
    background-color: #1f2937;
    border-right: 2px solid #ffcc00;
}
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
conn = sqlite3.connect('guia_santa_teresa.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS comercios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, ubicacion TEXT, foto_url TEXT, reseña_willian TEXT, estrellas_w INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS opiniones (id INTEGER PRIMARY KEY AUTOINCREMENT, comercio_id INTEGER, usuario TEXT, comentario TEXT, estrellas_u INTEGER, fecha TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS ajustes (id INTEGER PRIMARY KEY, logo_url TEXT)')
# Tabla para el contador de visitas
c.execute('CREATE TABLE IF NOT EXISTS visitas (fecha TEXT PRIMARY KEY, conteo INTEGER)')
conn.commit()

# --- REGISTRO DE VISITA DIARIA ---
fecha_hoy = datetime.now().strftime("%Y-%m-%d")
c.execute("INSERT OR IGNORE INTO visitas (fecha, conteo) VALUES (?, 0)", (fecha_hoy,))
c.execute("UPDATE visitas SET conteo = conteo + 1 WHERE fecha = ?", (fecha_hoy,))
conn.commit()

# --- CARGA DE LOGO ---
c.execute("SELECT logo_url FROM ajustes WHERE id=1")
res_logo = c.fetchone()
current_logo = res_logo[0] if res_logo else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"

# --- CABECERA ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)
st.markdown(f'<div class="logo-container"><img src="{current_logo}" class="app-logo" width="180"></div>', unsafe_allow_html=True)
st.title("🚀 Guía Comercial Almenar")

# --- CONTROL POR PESTAÑAS PRINCIPALES (TAB) ---
tab_publico, tab_llave_admin = st.tabs(["🏪 Guía Comercial", "🔑 Panel de Control"])

with tab_llave_admin:
    st.markdown("### ⚙️ Gestión de Sistema")
    with st.expander("Abrir Cerradura Administrativa", expanded=False):
        admin_pass = st.text_input("Introduce la clave maestra", type="password", key="pass_admin_main")
        if admin_pass == "Juan*316*":
            st.success("Modo Editor Total Activado")
            
            # --- SECCIÓN DE ESTADÍSTICAS (CONTADOR) ---
            st.markdown("### 📊 Estadísticas de Visitas")
            df_visitas = pd.read_sql_query("SELECT fecha as 'Fecha', conteo as 'Usuarios' FROM visitas ORDER BY fecha DESC LIMIT 7", conn)
            st.table(df_visitas)
            
            lista_categorias = ["Salud", "Farmacias", "Ópticas", "Ferretería", "Abastos", "Supermerkados", "Electrodomésticos", "Telefonía", "Carnicerías", "Tienda de ropa", "Servicios"]
            
            accion = st.radio("Acción:", ["Añadir", "Modificar/Quitar", "Borrar Negocio", "Ajustes Logo"], horizontal=True)
            
            if accion == "Añadir":
                with st.form("admin_add"):
                    n = st.text_input("Nombre del Negocio")
                    cat = st.selectbox("Categoría", lista_categorias)
                    ub = st.text_input("Ubicación")
                    up_file = st.file_uploader("Subir foto de negocio (PC)", type=['png', 'jpg', 'jpeg'])
                    url_img = st.text_input("O Link de Imagen", value="https://via.placeholder.com/600x300")
                    res = st.text_area("Escribir Reseña Inicial")
                    if st.form_submit_button("Guardar Negocio"):
                        final_img = url_img
                        if up_file:
                            final_img = f"data:image/png;base64,{base64.b64encode(up_file.read()).decode()}"
                        c.execute("INSERT INTO comercios (nombre, categoria, ubicacion, foto_url, reseña_willian, estrellas_w) VALUES (?,?,?,?,?,?)", (n, cat, ub, final_img, res, 5))
                        conn.commit()
                        st.rerun()

            elif accion == "Modificar/Quitar":
                df_mod = pd.read_sql_query("SELECT * FROM comercios", conn)
                if not df_mod.empty:
                    target_mod = st.selectbox("Selecciona Negocio", df_mod['nombre'].tolist())
                    row = df_mod[df_mod['nombre'] == target_mod].iloc[0]
                    with st.form("edit_form"):
                        new_n = st.text_input("Editar Nombre", value=row['nombre'])
                        new_ub = st.text_input("Editar Ubicación", value=row['ubicacion'])
                        new_res = st.text_area("Modificar Reseña", value=row['reseña_willian'])
                        new_up_file = st.file_uploader("Nueva Foto", type=['png', 'jpg', 'jpeg'])
                        if st.form_submit_button("Actualizar Todo"):
                            if new_up_file:
                                img_data = f"data:image/png;base64,{base64.b64encode(new_up_file.read()).decode()}"
                                c.execute("UPDATE comercios SET nombre=?, ubicacion=?, reseña_willian=?, foto_url=? WHERE id=?", (new_n, new_ub, new_res, img_data, int(row['id'])))
                            else:
                                c.execute("UPDATE comercios SET nombre=?, ubicacion=?, reseña_willian=? WHERE id=?", (new_n, new_ub, new_res, int(row['id'])))
                            conn.commit()
                            st.rerun()
                        if st.form_submit_button("Quitar Reseña"):
                            c.execute("UPDATE comercios SET reseña_willian='' WHERE id=?", (int(row['id']),))
                            conn.commit()
                            st.rerun()

            elif accion == "Borrar Negocio":
                df_del = pd.read_sql_query("SELECT * FROM comercios", conn)
                if not df_del.empty:
                    target = st.selectbox("Negocio a eliminar:", df_del['nombre'].tolist())
                    if st.button("Confirmar Eliminación"):
                        c.execute("DELETE FROM comercios WHERE nombre=?", (target,))
                        conn.commit()
                        st.rerun()

            elif accion == "Ajustes Logo":
                st.write("Carga el logo de cabecera:")
                new_logo = st.file_uploader("Seleccionar Logo", type=['png', 'jpg', 'jpeg'])
                if new_logo and st.button("Aplicar Logo"):
                    encoded_logo = base64.b64encode(new_logo.read()).decode()
                    c.execute("INSERT OR REPLACE INTO ajustes (id, logo_url) VALUES (1, ?)", (f"data:image/png;base64,{encoded_logo}",))
                    conn.commit()
                    st.rerun()

with tab_publico:
    # --- BÚSQUEDA Y CONTENIDO ---
    busq = st.text_input("🔍 ¿Qué buscas hoy en Santa Teresa?")
    df = pd.read_sql_query("SELECT * FROM comercios", conn)
    if not df.empty:
        categorias_db = df['categoria'].unique().tolist()
        tabs_negocios = st.tabs(categorias_db if categorias_db else ["General"])
        for i, cat_name in enumerate(categorias_db):
            with tabs_negocios[i]:
                filtrado = df[(df['categoria'] == cat_name) & (df['nombre'].str.contains(busq, case=False))]
                for idx, r in filtrado.iterrows():
                    st.markdown(f"##### 🏢 **{r['nombre']}**")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.image(r['foto_url'], use_container_width=True)
                        st.write(f"📍 **Ubicación:** {r['ubicacion']}")
                        query_maps = urllib.parse.quote(f"{r['nombre']} {r['ubicacion']} Santa Teresa del Tuy")
                        st.markdown(f'<a href="https://www.google.com/maps/search/{query_maps}" target="_blank" class="maps-button">📍 Ver en Google Maps</a>', unsafe_allow_html=True)
                    with col2:
                        if r['reseña_willian']:
                            st.info(f"**Reseña de Willian:** {r['reseña_willian']}")
                        else:
                            st.write("*Sin reseña disponible por ahora.*")
                    st.markdown("---")

# --- PIE DE PÁGINA ---
st.markdown(f"""
<div class='footer-willian'>
    <span class='gold-text'>© {datetime.now().year} - Diseñada por Willian Almenar</span><br>
    Santa Teresa del Tuy 2026
</div>
""", unsafe_allow_html=True)
