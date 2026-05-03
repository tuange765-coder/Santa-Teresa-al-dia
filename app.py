
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
from PIL import Image
import base64
import io
import uuid
import random
import requests
import json
import os

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ZONA HORARIA DE VENEZUELA (UTC-4) ---
CARACAS_TZ = pytz.timezone('America/Caracas')

def get_fecha_hora_venezuela():
    ahora_utc = datetime.now(pytz.UTC)
    ahora_caracas = ahora_utc.astimezone(CARACAS_TZ)
    return ahora_caracas

# --- CONEXION A NEON (POSTGRESQL) ---
def init_connection():
    try:
        if "DATABASE_URL" in st.secrets:
            conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        else:
            st.error("No se encontro DATABASE_URL en secrets")
            st.stop()
        
        test_query = conn.query("SELECT 1 as test", ttl=0)
        if test_query.empty:
            st.error("No se pudo verificar la conexion")
            st.stop()
        return conn
    except Exception as e:
        st.error(f"Error de conexion: {str(e)}")
        st.stop()

conn = init_connection()

# --- CREACION DE TABLAS ---
def create_tables():
    try:
        with conn.session as s:
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                categoria VARCHAR(50),
                contenido TEXT,
                imagen_url TEXT,
                fecha_publicacion VARCHAR(50),
                fecha_completa TIMESTAMP,
                autor VARCHAR(100),
                fuente VARCHAR(255)
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS reflexiones (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                contenido TEXT,
                versiculo VARCHAR(255),
                autor VARCHAR(100),
                fecha VARCHAR(50),
                activo BOOLEAN DEFAULT TRUE
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS ventana_pasado (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                contenido TEXT,
                fecha_evento VARCHAR(50),
                imagen_url TEXT,
                fecha_publicacion VARCHAR(50)
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS cronicas_reales (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                contenido TEXT,
                autor VARCHAR(100),
                fecha VARCHAR(50),
                lugar VARCHAR(255)
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                url TEXT,
                fecha_subida VARCHAR(50)
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS musicas (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                url TEXT,
                fecha_subida VARCHAR(50)
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS denuncias (
                id SERIAL PRIMARY KEY,
                denunciante VARCHAR(255),
                titulo VARCHAR(255),
                descripcion TEXT,
                ubicacion VARCHAR(255),
                fecha VARCHAR(50),
                estatus VARCHAR(50) DEFAULT 'Pendiente'
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS opiniones (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(100),
                comentario TEXT,
                calificacion INTEGER,
                fecha VARCHAR(50),
                aprobada BOOLEAN DEFAULT FALSE
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 0
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                logo_data TEXT,
                dolar_bcv REAL DEFAULT 60.0,
                ultima_actualizacion_dolar VARCHAR(50),
                ultima_actualizacion_noticias VARCHAR(50)
            )
            """))
            
            res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            
            res_c = s.execute(text("SELECT id FROM configuracion WHERE id = 1")).fetchone()
            if not res_c:
                s.execute(text("INSERT INTO configuracion (id, logo_data, dolar_bcv, ultima_actualizacion_dolar, ultima_actualizacion_noticias) VALUES (1, NULL, 60.0, NULL, NULL)"))
            
            # Cargar cronica historica de los Valles del Tuy si no existe
            cronicas = s.execute(text("SELECT COUNT(*) FROM cronicas_reales")).fetchone()
            if cronicas[0] == 0:
                s.execute(text("""
                    INSERT INTO cronicas_reales (titulo, contenido, autor, fecha, lugar)
                    VALUES ('Los Valles del Tuy: Cuna de la Independencia', 
                    'Los Valles del Tuy, tierra de hombres y mujeres valientes, fue escenario de importantes batallas durante la Guerra de Independencia. En 1814, el Libertador Simon Bolivar acampo en estas tierras antes de la Batalla de La Victoria. La valentia de los tuyeros quedo grabada en la historia patria. Hoy, Santa Teresa del Tuy y sus pueblos vecinos honran ese legado de libertad y resistencia.',
                    'Cronista Oficial', '1814', 'Valles del Tuy')
                """), {"t": "Cronica", "c": "Contenido", "a": "Autor", "f": "Fecha", "l": "Lugar"})
                s.commit()
            
            # Cargar reflexion cristiana inicial
            reflexiones = s.execute(text("SELECT COUNT(*) FROM reflexiones")).fetchone()
            if reflexiones[0] == 0:
                s.execute(text("""
                    INSERT INTO reflexiones (titulo, contenido, versiculo, autor, fecha, activo)
                    VALUES ('La Paz que Sobrepasa Todo Entendimiento',
                    'No se angustien por nada; más bien, presenten sus peticiones delante de Dios. La paz de Dios, que sobrepasa todo entendimiento, cuidara sus corazones y sus pensamientos.',
                    'Filipenses 4:6-7',
                    'Ministerio Santa Teresa', '2026-01-01', TRUE)
                """), {"t": "Titulo", "c": "Contenido", "v": "Versiculo", "a": "Autor", "f": "Fecha", "act": True})
                s.commit()
            
            s.commit()
    except Exception as e:
        st.error(f"Error al crear tablas: {str(e)}")

create_tables()

# --- FUNCION PARA OBTENER DOLAR BCV DESDE API ---
def obtener_dolar_bcv():
    """Obtiene el precio del dolar desde el BCV o fuentes oficiales"""
    try:
        # API alternativa confiable
        url = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Buscar el precio del dolar BCV
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and "price" in value:
                        return float(value["price"])
        return None
    except:
        return None

def actualizar_dolar_auto():
    """Actualiza automaticamente el precio del dolar desde el BCV"""
    try:
        ahora = get_fecha_hora_venezuela()
        fecha_hoy = ahora.strftime("%d/%m/%Y")
        
        # Verificar si ya se actualizo hoy
        res = conn.query("SELECT ultima_actualizacion_dolar FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty and res.iloc[0,0] == fecha_hoy:
            return  # Ya actualizado hoy
        
        nuevo_precio = obtener_dolar_bcv()
        if nuevo_precio:
            with conn.session as s:
                s.execute(text("UPDATE configuracion SET dolar_bcv = :p, ultima_actualizacion_dolar = :f WHERE id = 1"),
                         {"p": nuevo_precio, "f": fecha_hoy})
                s.commit()
    except:
        pass

def obtener_precio_dolar():
    try:
        res = conn.query("SELECT dolar_bcv FROM configuracion WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 60.0
    except:
        return 60.0

# --- FUNCIONES DE UTILIDAD ---
def actualizar_contador():
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

def obtener_logo():
    try:
        res = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty and res.iloc[0,0] else None
    except:
        return None

def guardar_logo(logo_b64):
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET logo_data = :l WHERE id = 1"), {"l": logo_b64})
            s.commit()
            return True
    except:
        return False

def obtener_efemerides():
    ahora = get_fecha_hora_venezuela()
    dia = ahora.day
    mes = ahora.month
    efemerides = {
        (1,1): "Año Nuevo - Fundacion de Santa Teresa del Tuy (1781)",
        (19,4): "Declaracion de la Independencia (1810)",
        (24,6): "Batalla de Carabobo - Dia del Ejercito",
        (5,7): "Firma del Acta de Independencia (1811)",
        (24,7): "Natalicio del Libertador Simon Bolivar",
        (12,10): "Dia de la Resistencia Indigena",
        (25,12): "Navidad - Nacimiento del Niño Jesus"
    }
    return efemerides.get((dia, mes), f"{dia} de {ahora.strftime('%B')} de {ahora.year}")

def imagen_a_base64(file):
    if file:
        try:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((800, 800))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70)
            return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        except:
            return None
    return None

def obtener_video_youtube_id(url):
    """Extrae el ID de un video de YouTube"""
    if "youtu.be" in url:
        return url.split("/")[-1]
    elif "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return url

# --- ACTUALIZAR DOLAR AUTOMATICAMENTE ---
actualizar_dolar_auto()

# --- FUNCIONES NOTICIAS ---
def publicar_noticia(titulo, categoria, contenido, imagen, fuente):
    try:
        ahora = get_fecha_hora_venezuela()
        img_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, imagen_url, fecha_publicacion, fecha_completa, autor, fuente)
                VALUES (:t, :c, :cont, :img, :f, :fc, 'Admin', :fuente)
            """), {"t": titulo, "c": categoria, "cont": contenido, "img": img_url,
                   "f": ahora.strftime("%d/%m/%Y"), "fc": ahora, "fuente": fuente})
            s.commit()
        return True
    except:
        return False

def obtener_noticias(categoria=None):
    try:
        if categoria and categoria != "Todas":
            return conn.query("SELECT * FROM noticias WHERE categoria = :cat ORDER BY fecha_completa DESC", 
                            params={"cat": categoria}, ttl=0)
        else:
            return conn.query("SELECT * FROM noticias ORDER BY fecha_completa DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_noticia(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM noticias WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES VIDEOS ---
def guardar_video(titulo, url):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO videos (titulo, url, fecha_subida)
                VALUES (:t, :u, :f)
            """), {"t": titulo, "u": url, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_videos():
    try:
        return conn.query("SELECT * FROM videos ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_video(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM videos WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES MUSICA ---
def guardar_musica(titulo, url):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO musicas (titulo, url, fecha_subida)
                VALUES (:t, :u, :f)
            """), {"t": titulo, "u": url, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_musicas():
    try:
        return conn.query("SELECT * FROM musicas ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_musica(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM musicas WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES REFLEXIONES ---
def guardar_reflexion(titulo, contenido, versiculo):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("UPDATE reflexiones SET activo = FALSE"))
            s.execute(text("""
                INSERT INTO reflexiones (titulo, contenido, versiculo, autor, fecha, activo)
                VALUES (:t, :c, :v, 'Admin', :f, TRUE)
            """), {"t": titulo, "c": contenido, "v": versiculo, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_reflexion_activa():
    try:
        df = conn.query("SELECT * FROM reflexiones WHERE activo = TRUE LIMIT 1", ttl=0)
        return df.iloc[0] if not df.empty else None
    except:
        return None

def obtener_reflexiones():
    try:
        return conn.query("SELECT * FROM reflexiones ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_reflexion(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM reflexiones WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES VENTANA PASADO ---
def guardar_ventana_pasado(titulo, contenido, fecha_evento, imagen):
    try:
        img_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO ventana_pasado (titulo, contenido, fecha_evento, imagen_url, fecha_publicacion)
                VALUES (:t, :c, :f, :img, :fp)
            """), {"t": titulo, "c": contenido, "f": fecha_evento, "img": img_url, "fp": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_ventana_pasado():
    try:
        return conn.query("SELECT * FROM ventana_pasado ORDER BY fecha_evento DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_ventana_pasado(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM ventana_pasado WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES CRONICAS ---
def guardar_cronica(titulo, contenido, lugar):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO cronicas_reales (titulo, contenido, autor, fecha, lugar)
                VALUES (:t, :c, 'Admin', :f, :l)
            """), {"t": titulo, "c": contenido, "f": ahora.strftime("%d/%m/%Y"), "l": lugar})
            s.commit()
        return True
    except:
        return False

def obtener_cronicas():
    try:
        return conn.query("SELECT * FROM cronicas_reales ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_cronica(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM cronicas_reales WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES DENUNCIAS ---
def guardar_denuncia(denunciante, titulo, descripcion, ubicacion):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO denuncias (denunciante, titulo, descripcion, ubicacion, fecha, estatus)
                VALUES (:d, :t, :desc, :u, :f, 'Pendiente')
            """), {"d": denunciante or "Anonimo", "t": titulo, "desc": descripcion, 
                   "u": ubicacion, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_denuncias():
    try:
        return conn.query("SELECT * FROM denuncias ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def actualizar_estatus_denuncia(id_, estatus):
    try:
        with conn.session as s:
            s.execute(text("UPDATE denuncias SET estatus = :e WHERE id = :id"), {"e": estatus, "id": id_})
            s.commit()
        return True
    except:
        return False

def eliminar_denuncia(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM denuncias WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES OPINIONES ---
def guardar_opinion(usuario, comentario, calificacion):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO opiniones (usuario, comentario, calificacion, fecha, aprobada)
                VALUES (:u, :c, :cal, :f, FALSE)
            """), {"u": usuario, "c": comentario, "cal": calificacion, 
                   "f": ahora.strftime("%d/%m/%Y %I:%M %p")})
            s.commit()
        return True
    except:
        return False

def obtener_opiniones(aprobadas=True):
    try:
        if aprobadas:
            return conn.query("SELECT * FROM opiniones WHERE aprobada = TRUE ORDER BY id DESC", ttl=0)
        else:
            return conn.query("SELECT * FROM opiniones ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def aprobar_opinion(id_):
    try:
        with conn.session as s:
            s.execute(text("UPDATE opiniones SET aprobada = TRUE WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

def eliminar_opinion(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM opiniones WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- CONTADOR DE VISITAS ---
if 'visitado' not in st.session_state:
    actualizar_contador()
    st.session_state.visitado = True

# --- ESTILOS CSS ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%);
    background-attachment: fixed;
}
.main > div {
    background-color: rgba(0, 0, 0, 0.65);
    border-radius: 20px;
    padding: 20px;
    margin: 10px 0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(0,0,0,0.9), rgba(0,36,125,0.95), rgba(207,20,43,0.95)) !important;
    border-right: 3px solid #FFD700;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
h1, h2, h3, h4 {
    color: #FFD700 !important;
}
p, span, label {
    color: #FFFFFF !important;
}
.stButton > button {
    background: linear-gradient(135deg, #FFD700, #CF142B);
    color: white !important;
    border: none;
    font-weight: bold;
    border-radius: 25px;
}
.stButton > button:hover {
    transform: scale(1.02);
}
input, textarea, .stSelectbox {
    background-color: rgba(255, 255, 255, 0.95) !important;
    color: #000000 !important;
    border-radius: 12px;
    border: 2px solid #FFD700 !important;
}
.stats-panel {
    background: rgba(0, 0, 0, 0.6);
    padding: 15px;
    border-radius: 20px;
    border: 2px solid #FFD700;
    text-align: center;
    margin-bottom: 20px;
}
.bronze-footer {
    background: linear-gradient(145deg, #8c6a31, #5d431a);
    border: 5px solid #d4af37;
    padding: 25px;
    border-radius: 20px;
    text-align: center;
    margin-top: 50px;
}
.bronze-footer p {
    color: #ffd700 !important;
}
</style>
""", unsafe_allow_html=True)

# --- OBTENER FECHA Y HORA CORRECTA DE VENEZUELA ---
ahora = get_fecha_hora_venezuela()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- ENCABEZADO ---
logo_data = obtener_logo()
if logo_data:
    st.markdown(f'<div style="text-align: center;"><img src="{logo_data}" style="max-width: 200px;"></div>', unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align: center; margin-bottom: 20px;">
    <div style="background: linear-gradient(135deg, #FFD700, #00247D, #CF142B); border-radius: 20px; padding: 20px;">
        <h1 style="color: white;">🌟 Santa Teresa al Dia 🌟</h1>
        <p style="color: white;">Informacion, Cultura y Fe para Nuestra Comunidad</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style="text-align: center;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png" 
             style="width: 150px; border-radius: 15px; border: 2px solid #FFD700;">
        <h2 style="color: #FFD700;">Santa Teresa</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    menu = st.radio("Menu Principal", [
        "🏠 Portada", "📰 Noticias", "🙏 Reflexiones", "🎬 Multimedia",
        "🏪 Guia Comercial", "📜 Ventana del Pasado", "✍️ Cronicas Reales",
        "⚠️ Denuncias", "💬 Opiniones"
    ], index=0)
    
    st.markdown("---")
    
    es_admin = False
    with st.expander("🔐 Administrador", expanded=False):
        clave = st.text_input("Clave:", type="password")
        if clave == "Juan*316*" or clave == "1966":
            es_admin = True
            st.success("✅ Acceso concedido")
        elif clave:
            st.error("❌ Clave incorrecta")

# --- PANEL DE ADMINISTRACION 100% FUNCIONAL ---
if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠️ Panel de Control")
    
    admin_tab = st.sidebar.radio("Seleccionar Accion", [
        "📝 Noticias",
        "🎬 Videos",
        "🎵 Musica",
        "🙏 Reflexiones",
        "📜 Ventana del Pasado",
        "✍️ Cronicas",
        "⚠️ Denuncias",
        "💬 Opiniones",
        "🎨 Configurar"
    ])
    
    # --- GESTION NOTICIAS ---
    if admin_tab == "📝 Noticias":
        st.write("### Publicar Noticia")
        with st.form("form_noticia"):
            titulo = st.text_input("Titulo")
            categoria = st.selectbox("Categoria", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=200)
            fuente = st.text_input("Fuente", placeholder="Ej: Efecto Cocuyo, TalCual, etc.")
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Publicar Noticia"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido, imagen, fuente):
                        st.success("Noticia publicada!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Noticias Existentes")
        noticias = obtener_noticias()
        for _, n in noticias.iterrows():
            with st.expander(f"{n['titulo']} - {n['fecha_publicacion']}"):
                st.write(n['contenido'])
                if st.button("Eliminar", key=f"del_not_{n['id']}"):
                    eliminar_noticia(n['id'])
                    st.rerun()
    
    # --- GESTION VIDEOS ---
    elif admin_tab == "🎬 Videos":
        st.write("### Agregar Video")
        with st.form("form_video"):
            titulo = st.text_input("Titulo del Video")
            url = st.text_input("URL de YouTube", placeholder="https://www.youtube.com/watch?v=...")
            if st.form_submit_button("Agregar Video"):
                if titulo and url:
                    if guardar_video(titulo, url):
                        st.success("Video agregado!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Videos Existentes")
        videos = obtener_videos()
        for _, v in videos.iterrows():
            with st.expander(v['titulo']):
                st.video(obtener_video_youtube_id(v['url']))
                if st.button("Eliminar", key=f"del_vid_{v['id']}"):
                    eliminar_video(v['id'])
                    st.rerun()
    
    # --- GESTION MUSICA ---
    elif admin_tab == "🎵 Musica":
        st.write("### Agregar Musica")
        with st.form("form_musica"):
            titulo = st.text_input("Titulo de la Cancion")
            url = st.text_input("URL del audio", placeholder="https://ejemplo.com/audio.mp3")
            if st.form_submit_button("Agregar Musica"):
                if titulo and url:
                    if guardar_musica(titulo, url):
                        st.success("Musica agregada!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Canciones Existentes")
        musicas = obtener_musicas()
        for _, m in musicas.iterrows():
            with st.expander(m['titulo']):
                st.audio(m['url'])
                if st.button("Eliminar", key=f"del_mus_{m['id']}"):
                    eliminar_musica(m['id'])
                    st.rerun()
    
    # --- GESTION REFLEXIONES ---
    elif admin_tab == "🙏 Reflexiones":
        st.write("### Nueva Reflexion")
        with st.form("form_reflexion"):
            titulo = st.text_input("Titulo")
            versiculo = st.text_input("Versiculo", placeholder="Ej: Juan 3:16")
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("Guardar Reflexion"):
                if titulo and contenido:
                    if guardar_reflexion(titulo, contenido, versiculo):
                        st.success("Reflexion guardada!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Reflexiones Anteriores")
        reflexiones = obtener_reflexiones()
        for _, r in reflexiones.iterrows():
            with st.expander(f"{r['titulo']} - {r['fecha']}"):
                st.write(r['contenido'])
                if st.button("Eliminar", key=f"del_ref_{r['id']}"):
                    eliminar_reflexion(r['id'])
                    st.rerun()
    
    # --- GESTION VENTANA DEL PASADO ---
    elif admin_tab == "📜 Ventana del Pasado":
        st.write("### Agregar Registro Historico")
        with st.form("form_ventana"):
            titulo = st.text_input("Titulo")
            fecha_evento = st.text_input("Fecha", placeholder="Ej: 15 de septiembre de 1781")
            contenido = st.text_area("Descripcion", height=150)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Guardar Registro"):
                if titulo and contenido:
                    if guardar_ventana_pasado(titulo, contenido, fecha_evento, imagen):
                        st.success("Registro guardado!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Registros Existentes")
        registros = obtener_ventana_pasado()
        for _, r in registros.iterrows():
            with st.expander(f"{r['titulo']} - {r['fecha_evento']}"):
                if r['imagen_url']:
                    st.image(r['imagen_url'], width=200)
                st.write(r['contenido'])
                if st.button("Eliminar", key=f"del_vent_{r['id']}"):
                    eliminar_ventana_pasado(r['id'])
                    st.rerun()
    
    # --- GESTION CRONICAS ---
    elif admin_tab == "✍️ Cronicas":
        st.write("### Nueva Cronica")
        with st.form("form_cronica"):
            titulo = st.text_input("Titulo")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("Guardar Cronica"):
                if titulo and contenido:
                    if guardar_cronica(titulo, contenido, lugar):
                        st.success("Cronica guardada!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Cronicas Existentes")
        cronicas = obtener_cronicas()
        for _, c in cronicas.iterrows():
            with st.expander(f"{c['titulo']} - {c['lugar']}"):
                st.write(c['contenido'])
                if st.button("Eliminar", key=f"del_cron_{c['id']}"):
                    eliminar_cronica(c['id'])
                    st.rerun()
    
    # --- GESTION DENUNCIAS ---
    elif admin_tab == "⚠️ Denuncias":
        st.write("### Gestion de Denuncias")
        denuncias = obtener_denuncias()
        for _, d in denuncias.iterrows():
            with st.expander(f"{d['titulo']} - {d['estatus']}"):
                st.write(f"**Denunciante:** {d['denunciante']}")
                st.write(f"**Descripcion:** {d['descripcion']}")
                st.write(f"**Ubicacion:** {d['ubicacion']}")
                nuevo_estado = st.selectbox("Estado", ["Pendiente", "En revision", "Resuelta", "Descartada"], key=f"est_{d['id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Actualizar", key=f"upd_{d['id']}"):
                        actualizar_estatus_denuncia(d['id'], nuevo_estado)
                        st.rerun()
                with col2:
                    if st.button("Eliminar", key=f"del_den_{d['id']}"):
                        eliminar_denuncia(d['id'])
                        st.rerun()
    
    # --- GESTION OPINIONES ---
    elif admin_tab == "💬 Opiniones":
        st.write("### Gestion de Opiniones")
        st.write("#### Opiniones Pendientes")
        opiniones_pendientes = obtener_opiniones(aprobadas=False)
        for _, op in opiniones_pendientes.iterrows():
            if not op['aprobada']:
                with st.expander(f"{op['usuario']} - {op['fecha']}"):
                    st.write(op['comentario'])
                    if st.button("Aprobar", key=f"aprob_{op['id']}"):
                        aprobar_opinion(op['id'])
                        st.rerun()
                    if st.button("Eliminar", key=f"del_pend_{op['id']}"):
                        eliminar_opinion(op['id'])
                        st.rerun()
        
        st.markdown("---")
        st.write("#### Todas las Opiniones")
        todas_opiniones = obtener_opiniones(aprobadas=False)
        for _, op in todas_opiniones.iterrows():
            with st.expander(f"{op['usuario']} - {'✅ Aprobada' if op['aprobada'] else '⏳ Pendiente'}"):
                st.write(op['comentario'])
                if st.button("Eliminar", key=f"del_all_{op['id']}"):
                    eliminar_opinion(op['id'])
                    st.rerun()
    
    # --- CONFIGURAR APP ---
    elif admin_tab == "🎨 Configurar":
        st.write("### Configuracion de la App")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Logo de la App**")
            logo_actual = obtener_logo()
            if logo_actual:
                st.image(logo_actual, width=100)
            nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg"])
            if nuevo_logo and st.button("Guardar Logo"):
                logo_b64 = imagen_a_base64(nuevo_logo)
                if guardar_logo(logo_b64):
                    st.success("Logo guardado!")
                    st.rerun()
        
        with col2:
            st.write("**Actualizar Dolar BCV**")
            if st.button("Actualizar Dolar desde BCV"):
                nuevo_precio = obtener_dolar_bcv()
                if nuevo_precio:
                    with conn.session as s:
                        s.execute(text("UPDATE configuracion SET dolar_bcv = :p WHERE id = 1"), {"p": nuevo_precio})
                        s.commit()
                    st.success(f"Dolar actualizado a {nuevo_precio:.2f} Bs")
                    st.rerun()
                else:
                    st.error("No se pudo obtener el precio actual")

# --- PANEL SUPERIOR ---
visitas = obtener_visitas()
precio_dolar = obtener_precio_dolar()
efemeride = obtener_efemerides()

st.markdown(f"""
<div class="stats-panel">
    <span style="color: #FFD700;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color: white; font-size: 1.8em; font-weight: bold;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 Visitas: {visitas:,} | 💵 Dolar BCV: {precio_dolar:.2f} Bs</span>
</div>

<div style="background: linear-gradient(135deg, #1a3a5c, #0a1a3a); padding: 15px; border-radius: 15px; border-left: 5px solid #FFD700; margin-bottom: 20px;">
    <span style="color: #FFD700; font-weight: bold;">📅 EFEMERIDES DEL DIA</span><br>
    <span style="color: white;">{efemeride}</span>
</div>
""", unsafe_allow_html=True)

# --- CONTENIDO PRINCIPAL ---
if menu == "🏠 Portada":
    st.title("Santa Teresa al Dia")
    
    st.markdown("### 📰 Ultimas Noticias")
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.head(6).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:300]}...")
            st.caption(f"📅 {n['fecha_publicacion']} | 🏷️ {n['categoria']} | 📰 Fuente: {n['fuente'] if n['fuente'] else 'Santa Teresa al Dia'}")
            st.markdown("---")
    else:
        st.info("No hay noticias disponibles")

elif menu == "📰 Noticias":
    st.title("Noticias")
    
    tab_nac, tab_inter, tab_dep, tab_rep, tab_todas = st.tabs(["🇻🇪 Nacionales", "🌍 Internacionales", "⚽ Deportes", "📰 Reportajes", "📋 Todas"])
    
    categories = {
        "Nacional": tab_nac,
        "Internacional": tab_inter,
        "Deportes": tab_dep,
        "Reportajes": tab_rep
    }
    
    for categoria, tab in categories.items():
        with tab:
            noticias = obtener_noticias(categoria=categoria)
            if not noticias.empty:
                for _, n in noticias.iterrows():
                    st.markdown(f"### {n['titulo']}")
                    st.caption(f"📅 {n['fecha_publicacion']} | 📰 {n['fuente'] if n['fuente'] else 'Santa Teresa al Dia'}")
                    st.write(n['contenido'])
                    if es_admin:
                        if st.button("🗑️ Eliminar", key=f"del_{categoria}_{n['id']}"):
                            eliminar_noticia(n['id'])
                            st.rerun()
                    st.markdown("---")
            else:
                st.info(f"No hay noticias en {categoria}")
    
    with tab_todas:
        noticias = obtener_noticias()
        if not noticias.empty:
            for _, n in noticias.iterrows():
                st.markdown(f"### {n['titulo']}")
                st.caption(f"📅 {n['fecha_publicacion']} | 🏷️ {n['categoria']} | 📰 {n['fuente'] if n['fuente'] else 'Santa Teresa al Dia'}")
                st.write(n['contenido'])
                if es_admin:
                    if st.button("🗑️ Eliminar", key=f"del_tod_{n['id']}"):
                        eliminar_noticia(n['id'])
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No hay noticias disponibles")

elif menu == "🙏 Reflexiones":
    st.title("🙏 Pan de Vida y Reflexiones")
    
    reflexion = obtener_reflexion_activa()
    if reflexion is not None:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0,0,0,0.6), rgba(0,36,125,0.6)); 
                    padding: 35px; border-radius: 20px; border-left: 8px solid #FFD700; text-align: center;">
            <h2 style="color: #FFD700;">✨ {reflexion['titulo']} ✨</h2>
            <p style="font-size: 1.2em;">{reflexion['contenido']}</p>
            <p style="margin-top: 15px;"><i>"{reflexion['versiculo']}"</i></p>
            <p style="margin-top: 20px;"><i>— {reflexion['autor']}, {reflexion['fecha']}</i></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No hay reflexion activa para hoy")

elif menu == "🎬 Multimedia":
    st.title("🎬 Multimedia")
    
    tab_video, tab_audio, tab_radio = st.tabs(["🎥 Videos", "🎵 Musica", "📻 Radio Online"])
    
    with tab_video:
        videos = obtener_videos()
        if not videos.empty:
            for _, v in videos.iterrows():
                st.markdown(f"**{v['titulo']}**")
                st.video(obtener_video_youtube_id(v['url']))
                st.caption(f"Subido: {v['fecha_subida']}")
                st.markdown("---")
        else:
            st.info("No hay videos disponibles")
    
    with tab_audio:
        musicas = obtener_musicas()
        if not musicas.empty:
            for _, m in musicas.iterrows():
                st.markdown(f"**{m['titulo']}**")
                st.audio(m['url'])
                st.caption(f"Agregado: {m['fecha_subida']}")
                st.markdown("---")
        else:
            st.info("No hay musica disponible")
    
    with tab_radio:
        st.markdown("### 📻 Radio Online")
        st.markdown("**Escucha nuestra radio en vivo**")
        st.audio("https://streaming.listen2myradio.com/example", format="audio/mp3")
        st.caption("Radio Santa Teresa - 24/7 al aire")

elif menu == "🏪 Guia Comercial":
    st.title("🏪 Guia Comercial de Santa Teresa")
    st.markdown("""
    <div style="text-align: center; padding: 50px; background: rgba(0,0,0,0.5); border-radius: 25px;">
        <h2 style="color: #FFD700;">📱 Guia Comercial Almenar</h2>
        <p>Encuentra comercios, servicios y promociones en Santa Teresa del Tuy</p>
        <a href="https://williantuguiasantateresa.streamlit.app" target="_blank">
            <button style="background: linear-gradient(135deg, #FFD700, #CF142B); 
                           padding: 15px 35px; border-radius: 30px; border: none; 
                           color: white; font-size: 1.2em; cursor: pointer; margin-top: 20px;">
                🌐 Ir a la Guia Comercial
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

elif menu == "📜 Ventana del Pasado":
    st.title("📜 Ventana del Pasado")
    st.markdown("*Recordar es vivir... Viajemos a traves de la historia de Santa Teresa*")
    
    registros = obtener_ventana_pasado()
    if not registros.empty:
        for _, r in registros.iterrows():
            col1, col2 = st.columns([1, 2])
            with col1:
                if r['imagen_url']:
                    st.image(r['imagen_url'], use_container_width=True)
                else:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
            with col2:
                st.markdown(f"### 🏛️ {r['titulo']}")
                st.caption(f"📅 {r['fecha_evento']}")
                st.write(r['contenido'])
            st.markdown("---")
    else:
        st.info("Proximamente mas contenido historico")

elif menu == "✍️ Cronicas Reales":
    st.title("✍️ Cronicas Reales")
    st.markdown("*Historias y testimonios de nuestra gente*")
    
    cronicas = obtener_cronicas()
    if not cronicas.empty:
        for _, c in cronicas.iterrows():
            with st.expander(f"📖 {c['titulo']} - {c['lugar']}"):
                st.write(c['contenido'])
                st.caption(f"Publicado: {c['fecha']}")
    else:
        st.info("No hay cronicas publicadas aun")

elif menu == "⚠️ Denuncias":
    st.title("⚠️ Denuncias Ciudadanas")
    st.markdown("*Todas las denuncias son anonimas y seran investigadas*")
    
    tab_den, tab_ver = st.tabs(["📝 Hacer Denuncia", "📋 Ver Denuncias"])
    
    with tab_den:
        with st.form("form_denuncia"):
            nombre = st.text_input("Tu nombre (puede ser anonimo)")
            titulo = st.text_input("Titulo de la denuncia")
            desc = st.text_area("Descripcion detallada", height=150)
            ubic = st.text_input("Ubicacion del hecho")
            if st.form_submit_button("🚨 Enviar Denuncia"):
                if titulo and desc:
                    if guardar_denuncia(nombre, titulo, desc, ubic):
                        st.success("✅ Denuncia enviada. Las autoridades la revisaran.")
                        st.balloons()
                    else:
                        st.error("❌ Error al enviar")
                else:
                    st.warning("⚠️ Titulo y descripcion son obligatorios")
    
    with tab_ver:
        denuncias = obtener_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <strong>📌 {d['titulo']}</strong><br>
                    <span style="color: #FFD700;">Estado: {d['estatus']}</span><br>
                    <small>📍 {d['ubicacion']} | 📅 {d['fecha']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay denuncias para mostrar")

elif menu == "💬 Opiniones":
    st.title("💬 Opiniones de Nuestros Visitantes")
    
    tab_op, tab_ver = st.tabs(["💭 Dar Opinion", "📖 Ver Opiniones"])
    
    with tab_op:
        with st.form("form_opinion"):
            usuario = st.text_input("Tu nombre")
            comentario = st.text_area("Tu opinion", height=100)
            calificacion = st.slider("Calificacion", 1, 5, 5)
            if st.form_submit_button("Enviar Opinion"):
                if usuario and comentario:
                    if guardar_opinion(usuario, comentario, calificacion):
                        st.success("✅ Gracias por tu opinion! Sera revisada por el administrador.")
                        st.balloons()
                    else:
                        st.error("❌ Error al enviar")
                else:
                    st.warning("⚠️ Nombre y comentario son obligatorios")
    
    with tab_ver:
        opiniones = obtener_opiniones(aprobadas=True)
        if not opiniones.empty:
            for _, op in opiniones.iterrows():
                estrellas = "⭐" * op['calificacion']
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <strong>{op['usuario']}</strong> {estrellas}<br>
                    "{op['comentario']}"<br>
                    <small>📅 {op['fecha']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay opiniones aprobadas aun")

# --- FOOTER ---
st.markdown("""
<div class="bronze-footer">
    <p>⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproduccion total o parcial - Derechos Reservados</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
