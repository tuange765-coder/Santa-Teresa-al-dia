import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from sqlalchemy import text
from PIL import Image
import base64
import io
import random
import requests
import os
import tempfile

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide"
)

# --- ZONA HORARIA DE VENEZUELA ---
CARACAS_TZ = pytz.timezone('America/Caracas')

def get_fecha_hora_venezuela():
    ahora_utc = datetime.now(pytz.UTC)
    ahora_caracas = ahora_utc.astimezone(CARACAS_TZ)
    return ahora_caracas

# --- CONEXION A BASE DE DATOS ---
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

# --- FUNCION PARA RECREAR TABLAS ---
def recreate_tables():
    try:
        with conn.session as s:
            # Eliminar tablas existentes
            s.execute(text("DROP TABLE IF EXISTS noticias CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS negocios CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS reflexiones CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS ventana_pasado CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS cronicas_reales CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS videos CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS musicas CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS denuncias CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS opiniones CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS visitas CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS configuracion CASCADE"))
            s.commit()
            
            # Tabla de noticias
            s.execute(text("""
            CREATE TABLE noticias (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                categoria VARCHAR(100),
                contenido TEXT,
                imagen_url TEXT,
                fecha_publicacion VARCHAR(50),
                autor VARCHAR(200),
                fuente VARCHAR(300)
            )
            """))
            
            # Tabla de negocios (Donde ir / Donde comprar)
            s.execute(text("""
            CREATE TABLE negocios (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(500),
                categoria VARCHAR(200),
                reseña TEXT,
                imagen_url TEXT,
                direccion VARCHAR(500),
                telefono VARCHAR(100),
                horario VARCHAR(200),
                fecha_agregado VARCHAR(50)
            )
            """))
            
            # Tabla de reflexiones
            s.execute(text("""
            CREATE TABLE reflexiones (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                contenido TEXT,
                versiculo VARCHAR(300),
                autor VARCHAR(200),
                fecha VARCHAR(50),
                activo BOOLEAN DEFAULT TRUE
            )
            """))
            
            # Tabla de ventana del pasado
            s.execute(text("""
            CREATE TABLE ventana_pasado (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                contenido TEXT,
                fecha_evento VARCHAR(100),
                imagen_url TEXT,
                fecha_publicacion VARCHAR(50)
            )
            """))
            
            # Tabla de cronicas reales
            s.execute(text("""
            CREATE TABLE cronicas_reales (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                contenido TEXT,
                autor VARCHAR(200),
                fecha VARCHAR(50),
                lugar VARCHAR(300)
            )
            """))
            
            # Tabla de videos
            s.execute(text("""
            CREATE TABLE videos (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                video_data TEXT,
                formato VARCHAR(50),
                fecha_subida VARCHAR(50)
            )
            """))
            
            # Tabla de musicas
            s.execute(text("""
            CREATE TABLE musicas (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                audio_data TEXT,
                formato VARCHAR(50),
                fecha_subida VARCHAR(50)
            )
            """))
            
            # Tabla de denuncias
            s.execute(text("""
            CREATE TABLE denuncias (
                id SERIAL PRIMARY KEY,
                denunciante VARCHAR(300),
                titulo VARCHAR(500),
                descripcion TEXT,
                ubicacion VARCHAR(500),
                fecha VARCHAR(50),
                estatus VARCHAR(50) DEFAULT 'Pendiente'
            )
            """))
            
            # Tabla de opiniones
            s.execute(text("""
            CREATE TABLE opiniones (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(200),
                comentario TEXT,
                calificacion INTEGER,
                fecha VARCHAR(50),
                aprobada BOOLEAN DEFAULT FALSE
            )
            """))
            
            # Tabla de visitas
            s.execute(text("""
            CREATE TABLE visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 0
            )
            """))
            
            # Tabla de configuracion
            s.execute(text("""
            CREATE TABLE configuracion (
                id INTEGER PRIMARY KEY,
                logo_data TEXT,
                dolar_bcv REAL DEFAULT 60.0,
                ultima_actualizacion_dolar VARCHAR(50),
                ultimas_noticias_fecha VARCHAR(50)
            )
            """))
            
            # Insertar datos iniciales
            s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            s.execute(text("INSERT INTO configuracion (id, logo_data, dolar_bcv, ultimas_noticias_fecha) VALUES (1, NULL, 60.0, NULL)"))
            
            # Insertar cronica historica
            s.execute(text("""
                INSERT INTO cronicas_reales (titulo, contenido, autor, fecha, lugar)
                VALUES ('Los Valles del Tuy', 'Los Valles del Tuy, tierra de hombres y mujeres valientes, fue escenario de importantes batallas durante la Guerra de Independencia.', 'Cronista', '2026', 'Valles del Tuy')
            """))
            
            # Insertar reflexion inicial
            s.execute(text("""
                INSERT INTO reflexiones (titulo, contenido, versiculo, autor, fecha, activo)
                VALUES ('La Paz de Dios', 'No se angustien por nada; presenten sus peticiones delante de Dios.', 'Filipenses 4:6-7', 'Ministerio', '2026-01-01', TRUE)
            """))
            
            s.commit()
            st.success("Tablas creadas correctamente")
            
    except Exception as e:
        st.error(f"Error al crear tablas: {str(e)}")

recreate_tables()

# --- NOTICIAS AUTOMATICAS DIARIAS ---
def cargar_noticias_automaticas():
    """Carga noticias automaticamente si es un nuevo dia"""
    try:
        ahora = get_fecha_hora_venezuela()
        fecha_hoy = ahora.strftime("%d/%m/%Y")
        
        # Verificar si ya se cargaron noticias hoy
        res = conn.query("SELECT ultimas_noticias_fecha FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty and res.iloc[0,0] == fecha_hoy:
            return  # Ya cargadas hoy
        
        # Verificar si hay noticias existentes
        noticias_existentes = conn.query("SELECT COUNT(*) FROM noticias", ttl=0)
        if noticias_existentes.iloc[0,0] > 0:
            return  # Ya hay noticias
        
        # Noticias del dia
        noticias_diarias = [
            {"titulo": f"Buenos dias Santa Teresa - {fecha_hoy}", "categoria": "Nacional", "contenido": "Que tengas un excelente dia. Mantente informado con Santa Teresa al Dia.", "fuente": "Santa Teresa al Dia"},
            {"titulo": "Reporte del Clima", "categoria": "Nacional", "contenido": "Se espera un dia soleado con temperaturas agradables en los Valles del Tuy.", "fuente": "Clima Venezuela"},
            {"titulo": "Resumen Deportivo", "categoria": "Deportes", "contenido": "La Vinotinto se prepara para sus proximos compromisos internacionales.", "fuente": "Deportes Venezuela"},
            {"titulo": "Panorama Internacional", "categoria": "Internacional", "contenido": "Las noticias mas importantes del mundo en un solo lugar.", "fuente": "Internacional Press"},
            {"titulo": "Reportaje Especial", "categoria": "Reportajes", "contenido": "Historias de exito de emprendedores locales que transforman Santa Teresa.", "fuente": "Reportajes Locales"}
        ]
        
        with conn.session as s:
            for n in noticias_diarias:
                s.execute(text("""
                    INSERT INTO noticias (titulo, categoria, contenido, fecha_publicacion, autor, fuente)
                    VALUES (:t, :c, :cont, :f, 'Sistema Automatico', :fuente)
                """), {"t": n["titulo"], "c": n["categoria"], "cont": n["contenido"], 
                       "f": fecha_hoy, "fuente": n["fuente"]})
            s.execute(text("UPDATE configuracion SET ultimas_noticias_fecha = :f WHERE id = 1"), {"f": fecha_hoy})
            s.commit()
            
    except Exception as e:
        pass

# --- FUNCION DOLAR BCV ---
def obtener_dolar_bcv():
    try:
        url = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and "price" in value:
                        return float(value["price"])
        return None
    except:
        return None

def actualizar_dolar_auto():
    try:
        ahora = get_fecha_hora_venezuela()
        fecha_hoy = ahora.strftime("%d/%m/%Y")
        res = conn.query("SELECT ultima_actualizacion_dolar FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty and res.iloc[0,0] == fecha_hoy:
            return
        nuevo_precio = obtener_dolar_bcv()
        if nuevo_precio and nuevo_precio > 0:
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

# --- FUNCIONES UTILES ---
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
        return res.iloc[0,0] if not res.empty else None
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

def video_a_base64(file):
    if file:
        try:
            bytes_data = file.read()
            return base64.b64encode(bytes_data).decode()
        except:
            return None
    return None

def audio_a_base64(file):
    if file:
        try:
            bytes_data = file.read()
            return base64.b64encode(bytes_data).decode()
        except:
            return None
    return None

def mostrar_video(video_data, formato):
    try:
        video_bytes = base64.b64decode(video_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato}") as tmp_file:
            tmp_file.write(video_bytes)
            tmp_path = tmp_file.name
        st.video(tmp_path)
        os.unlink(tmp_path)
    except:
        st.error("Error al cargar el video")

def mostrar_musica(audio_data, formato):
    try:
        audio_bytes = base64.b64decode(audio_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato}") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        st.audio(tmp_path)
        os.unlink(tmp_path)
    except:
        st.error("Error al cargar el audio")

# --- FUNCIONES NOTICIAS ---
def publicar_noticia(titulo, categoria, contenido, imagen, fuente):
    try:
        ahora = get_fecha_hora_venezuela()
        img_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, imagen_url, fecha_publicacion, autor, fuente)
                VALUES (:t, :c, :cont, :img, :f, 'Admin', :fuente)
            """), {"t": titulo, "c": categoria, "cont": contenido, "img": img_url,
                   "f": ahora.strftime("%d/%m/%Y"), "fuente": fuente})
            s.commit()
        return True
    except:
        return False

def obtener_noticias(categoria=None):
    try:
        if categoria and categoria != "Todas":
            return conn.query("SELECT * FROM noticias WHERE categoria = :cat ORDER BY id DESC", 
                            params={"cat": categoria}, ttl=0)
        else:
            return conn.query("SELECT * FROM noticias ORDER BY id DESC", ttl=0)
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

# --- FUNCIONES NEGOCIOS (Donde ir / Donde comprar) ---
def agregar_negocio(nombre, categoria, reseña, direccion, telefono, horario, imagen):
    try:
        img_url = imagen_a_base64(imagen) if imagen else None
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO negocios (nombre, categoria, reseña, imagen_url, direccion, telefono, horario, fecha_agregado)
                VALUES (:n, :c, :r, :i, :d, :t, :h, :f)
            """), {"n": nombre, "c": categoria, "r": reseña, "i": img_url, 
                   "d": direccion, "t": telefono, "h": horario, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_negocios(categoria=None):
    try:
        if categoria and categoria != "Todos":
            return conn.query("SELECT * FROM negocios WHERE categoria = :cat ORDER BY id DESC", 
                            params={"cat": categoria}, ttl=0)
        else:
            return conn.query("SELECT * FROM negocios ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_negocio(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM negocios WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- FUNCIONES VIDEOS ---
def guardar_video(titulo, archivo_video):
    try:
        ahora = get_fecha_hora_venezuela()
        video_b64 = video_a_base64(archivo_video)
        formato = archivo_video.type.split("/")[-1] if archivo_video.type else "mp4"
        with conn.session as s:
            s.execute(text("""
                INSERT INTO videos (titulo, video_data, formato, fecha_subida)
                VALUES (:t, :v, :fmt, :f)
            """), {"t": titulo, "v": video_b64, "fmt": formato, "f": ahora.strftime("%d/%m/%Y")})
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
def guardar_musica(titulo, archivo_audio):
    try:
        ahora = get_fecha_hora_venezuela()
        audio_b64 = audio_a_base64(archivo_audio)
        formato = archivo_audio.type.split("/")[-1] if archivo_audio.type else "mp3"
        with conn.session as s:
            s.execute(text("""
                INSERT INTO musicas (titulo, audio_data, formato, fecha_subida)
                VALUES (:t, :a, :fmt, :f)
            """), {"t": titulo, "a": audio_b64, "fmt": formato, "f": ahora.strftime("%d/%m/%Y")})
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
def guardar_ventana(titulo, contenido, fecha_evento, imagen):
    try:
        img_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO ventana_pasado (titulo, contenido, fecha_evento, imagen_url, fecha_publicacion)
                VALUES (:t, :c, :f, :img, :fp)
            """), {"t": titulo, "c": contenido, "f": fecha_evento, "img": img_url, 
                   "fp": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def obtener_ventana():
    try:
        return conn.query("SELECT * FROM ventana_pasado ORDER BY fecha_evento DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_ventana(id_):
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

def actualizar_estatus(id_, estatus):
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

# --- CARGAR NOTICIAS AUTOMATICAS ---
cargar_noticias_automaticas()
actualizar_dolar_auto()

# --- CONTADOR VISITAS ---
if 'visitado' not in st.session_state:
    actualizar_contador()
    st.session_state.visitado = True

# --- ESTILOS CSS ---
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%); background-attachment: fixed; }
.main > div { background-color: rgba(0,0,0,0.65); border-radius: 20px; padding: 20px; margin: 10px 0; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, rgba(0,0,0,0.9), rgba(0,36,125,0.95), rgba(207,20,43,0.95)) !important; border-right: 3px solid #FFD700; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
h1, h2, h3, h4 { color: #FFD700 !important; }
p, span, label { color: #FFFFFF !important; }
.stButton > button { background: linear-gradient(135deg, #FFD700, #CF142B); color: white !important; border: none; font-weight: bold; border-radius: 25px; }
.stButton > button:hover { transform: scale(1.02); }
input, textarea, .stSelectbox { background-color: rgba(255,255,255,0.95) !important; color: #000000 !important; border-radius: 12px; border: 2px solid #FFD700 !important; }
.stats-panel { background: rgba(0,0,0,0.6); padding: 15px; border-radius: 20px; border: 2px solid #FFD700; text-align: center; margin-bottom: 20px; }
.bronze-footer { background: linear-gradient(145deg, #8c6a31, #5d431a); border: 5px solid #d4af37; padding: 25px; border-radius: 20px; text-align: center; margin-top: 50px; }
.bronze-footer p { color: #ffd700 !important; }
</style>
""", unsafe_allow_html=True)

# --- FECHA Y HORA ---
ahora = get_fecha_hora_venezuela()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- ENCABEZADO ---
logo = obtener_logo()
if logo:
    st.markdown(f'<div style="text-align: center;"><img src="{logo}" style="max-width: 200px;"></div>', unsafe_allow_html=True)

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
        "Portada", "Noticias", "Donde ir - Donde comprar", "Reflexiones", "Multimedia",
        "Ventana del Pasado", "Cronicas Reales", "Denuncias", "Opiniones"
    ], index=0)
    
    st.markdown("---")
    
    es_admin = False
    with st.expander("Administrador", expanded=False):
        clave = st.text_input("Clave:", type="password")
        if clave == "Juan*316*" or clave == "1966":
            es_admin = True
            st.success("Acceso concedido")
        elif clave:
            st.error("Clave incorrecta")

# --- PANEL DE ADMINISTRACION ---
if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Panel de Control")
    
    admin_tab = st.sidebar.radio("Accion", [
        "Noticias", "Donde ir - Donde comprar", "Videos", "Musica", 
        "Reflexiones", "Ventana Pasado", "Cronicas", "Denuncias", "Opiniones", "Configurar"
    ])
    
    # Admin: Noticias
    if admin_tab == "Noticias":
        st.write("### Publicar Noticia")
        with st.form("form_noticia"):
            titulo = st.text_input("Titulo")
            categoria = st.selectbox("Categoria", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=200)
            fuente = st.text_input("Fuente")
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Publicar"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido, imagen, fuente):
                        st.success("Noticia publicada!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Noticias Existentes")
        for _, n in obtener_noticias().iterrows():
            with st.expander(f"{n['titulo']}"):
                if n['imagen_url']:
                    st.image(n['imagen_url'], width=200)
                st.write(n['contenido'])
                if st.button("Eliminar", key=f"del_{n['id']}"):
                    eliminar_noticia(n['id'])
                    st.rerun()
    
    # Admin: Donde ir - Donde comprar (Negocios)
    elif admin_tab == "Donde ir - Donde comprar":
        st.write("### Agregar Negocio o Lugar")
        with st.form("form_negocio"):
            nombre = st.text_input("Nombre del Negocio/Lugar")
            categoria_neg = st.text_input("Categoria", placeholder="Ej: Restaurante, Tienda, Parque, Iglesia")
            reseña = st.text_area("Reseña / Descripcion", height=100)
            direccion = st.text_input("Direccion")
            telefono = st.text_input("Telefono", placeholder="Ej: 0412-1234567")
            horario = st.text_input("Horario", placeholder="Ej: Lunes a Sabado 8am-6pm")
            imagen_neg = st.file_uploader("Foto del lugar", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Agregar Negocio"):
                if nombre and reseña:
                    if agregar_negocio(nombre, categoria_neg, reseña, direccion, telefono, horario, imagen_neg):
                        st.success("Negocio agregado!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Negocios Existentes")
        for _, n in obtener_negocios().iterrows():
            with st.expander(f"{n['nombre']} - {n['categoria']}"):
                if n['imagen_url']:
                    st.image(n['imagen_url'], width=200)
                st.write(f"**Reseña:** {n['reseña']}")
                st.write(f"**Direccion:** {n['direccion']}")
                st.write(f"**Telefono:** {n['telefono']}")
                st.write(f"**Horario:** {n['horario']}")
                if st.button("Eliminar", key=f"del_neg_{n['id']}"):
                    eliminar_negocio(n['id'])
                    st.rerun()
    
    # Admin: Videos
    elif admin_tab == "Videos":
        st.write("### Subir Video desde PC")
        with st.form("form_video"):
            titulo = st.text_input("Titulo del Video")
            archivo_video = st.file_uploader("Seleccionar video (MP4, AVI, MOV, MKV)", type=["mp4", "avi", "mov", "mkv"])
            if st.form_submit_button("Subir Video"):
                if titulo and archivo_video:
                    if guardar_video(titulo, archivo_video):
                        st.success("Video subido exitosamente!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Videos Existentes")
        for _, v in obtener_videos().iterrows():
            with st.expander(v['titulo']):
                mostrar_video(v['video_data'], v['formato'])
                if st.button("Eliminar", key=f"del_vid_{v['id']}"):
                    eliminar_video(v['id'])
                    st.rerun()
    
    # Admin: Musica
    elif admin_tab == "Musica":
        st.write("### Subir Musica desde PC")
        with st.form("form_musica"):
            titulo = st.text_input("Titulo de la Cancion")
            archivo_audio = st.file_uploader("Seleccionar audio (MP3, WAV, OGG)", type=["mp3", "wav", "ogg"])
            if st.form_submit_button("Subir Musica"):
                if titulo and archivo_audio:
                    if guardar_musica(titulo, archivo_audio):
                        st.success("Musica subida exitosamente!")
                        st.rerun()
        
        st.markdown("---")
        st.write("### Canciones Existentes")
        for _, m in obtener_musicas().iterrows():
            with st.expander(m['titulo']):
                mostrar_musica(m['audio_data'], m['formato'])
                if st.button("Eliminar", key=f"del_mus_{m['id']}"):
                    eliminar_musica(m['id'])
                    st.rerun()
    
    # Admin: Reflexiones
    elif admin_tab == "Reflexiones":
        st.write("### Nueva Reflexion")
        with st.form("form_reflexion"):
            titulo = st.text_input("Titulo")
            versiculo = st.text_input("Versiculo")
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("Guardar"):
                if titulo and contenido:
                    guardar_reflexion(titulo, contenido, versiculo)
                    st.success("Reflexion guardada!")
                    st.rerun()
        
        st.markdown("---")
        st.write("### Reflexiones Anteriores")
        for _, r in obtener_reflexiones().iterrows():
            with st.expander(f"{r['titulo']}"):
                st.write(r['contenido'])
                st.caption(f"Versiculo: {r['versiculo']}")
                if st.button("Eliminar", key=f"del_ref_{r['id']}"):
                    eliminar_reflexion(r['id'])
                    st.rerun()
    
    # Admin: Ventana Pasado
    elif admin_tab == "Ventana Pasado":
        st.write("### Nuevo Registro Historico")
        with st.form("form_ventana"):
            titulo = st.text_input("Titulo")
            fecha = st.text_input("Fecha")
            contenido = st.text_area("Descripcion", height=150)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Guardar"):
                if titulo and contenido:
                    guardar_ventana(titulo, contenido, fecha, imagen)
                    st.success("Registro guardado!")
                    st.rerun()
        
        st.markdown("---")
        st.write("### Registros Existentes")
        for _, v in obtener_ventana().iterrows():
            with st.expander(f"{v['titulo']}"):
                if v['imagen_url']:
                    st.image(v['imagen_url'], width=200)
                st.write(v['contenido'])
                if st.button("Eliminar", key=f"del_vent_{v['id']}"):
                    eliminar_ventana(v['id'])
                    st.rerun()
    
    # Admin: Cronicas
    elif admin_tab == "Cronicas":
        st.write("### Nueva Cronica")
        with st.form("form_cronica"):
            titulo = st.text_input("Titulo")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("Guardar"):
                if titulo and contenido:
                    guardar_cronica(titulo, contenido, lugar)
                    st.success("Cronica guardada!")
                    st.rerun()
        
        st.markdown("---")
        st.write("### Cronicas Existentes")
        for _, c in obtener_cronicas().iterrows():
            with st.expander(f"{c['titulo']}"):
                st.write(c['contenido'])
                if st.button("Eliminar", key=f"del_cron_{c['id']}"):
                    eliminar_cronica(c['id'])
                    st.rerun()
    
    # Admin: Denuncias
    elif admin_tab == "Denuncias":
        st.write("### Gestion Denuncias")
        for _, d in obtener_denuncias().iterrows():
            with st.expander(f"{d['titulo']}"):
                st.write(f"Denunciante: {d['denunciante']}")
                st.write(f"Descripcion: {d['descripcion']}")
                st.write(f"Ubicacion: {d['ubicacion']}")
                nuevo = st.selectbox("Estado", ["Pendiente", "En revision", "Resuelta", "Descartada"], key=f"est_{d['id']}")
                if st.button("Actualizar", key=f"upd_{d['id']}"):
                    actualizar_estatus(d['id'], nuevo)
                    st.rerun()
                if st.button("Eliminar", key=f"del_den_{d['id']}"):
                    eliminar_denuncia(d['id'])
                    st.rerun()
    
    # Admin: Opiniones
    elif admin_tab == "Opiniones":
        st.write("### Opiniones Pendientes")
        for _, op in obtener_opiniones(aprobadas=False).iterrows():
            if not op['aprobada']:
                with st.expander(f"{op['usuario']}"):
                    st.write(op['comentario'])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Aprobar", key=f"aprob_{op['id']}"):
                            aprobar_opinion(op['id'])
                            st.rerun()
                    with col2:
                        if st.button("Eliminar", key=f"del_op_{op['id']}"):
                            eliminar_opinion(op['id'])
                            st.rerun()
    
    # Admin: Configurar
    elif admin_tab == "Configurar":
        st.write("### Configuracion")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("Logo de la App")
            if logo:
                st.image(logo, width=100)
            nuevo = st.file_uploader("Subir logo", type=["png", "jpg"])
            if nuevo and st.button("Guardar Logo"):
                b64 = imagen_a_base64(nuevo)
                if guardar_logo(b64):
                    st.success("Logo guardado!")
                    st.rerun()
        
        with col2:
            st.write("Dolar BCV")
            actual = obtener_precio_dolar()
            st.write(f"Precio actual: {actual:.2f} Bs")
            if st.button("Actualizar desde BCV"):
                nuevo = obtener_dolar_bcv()
                if nuevo:
                    with conn.session as s:
                        s.execute(text("UPDATE configuracion SET dolar_bcv = :p WHERE id = 1"), {"p": nuevo})
                        s.commit()
                    st.success(f"Actualizado a {nuevo:.2f} Bs")
                    st.rerun()
                else:
                    st.error("No se pudo obtener el precio")

# --- PANEL SUPERIOR ---
visitas = obtener_visitas()
precio = obtener_precio_dolar()
efemerides = "Hoy conmemoramos la historia de Santa Teresa del Tuy"

st.markdown(f"""
<div class="stats-panel">
    <span style="color: #FFD700;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color: white; font-size: 1.8em;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 Visitas: {visitas:,} | 💵 Dolar BCV: {precio:.2f} Bs</span>
</div>
""", unsafe_allow_html=True)

# --- CONTENIDO PRINCIPAL ---
if menu == "Portada":
    st.title("Santa Teresa al Dia")
    st.markdown("### Ultimas Noticias")
    for _, n in obtener_noticias().head(5).iterrows():
        st.info(f"**{n['titulo']}**\n\n{n['contenido'][:300]}...")
        st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
        st.markdown("---")
    
    st.markdown("---")
    st.markdown("### Reflexion del Dia")
    ref = obtener_reflexion_activa()
    if ref:
        st.markdown(f"**{ref['titulo']}**")
        st.write(ref['contenido'])
        st.caption(f"{ref['versiculo']}")

elif menu == "Noticias":
    st.title("Noticias")
    cat = st.selectbox("Filtrar", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    for _, n in obtener_noticias(cat if cat != "Todas" else None).iterrows():
        st.markdown(f"### {n['titulo']}")
        st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
        st.write(n['contenido'])
        st.markdown("---")

elif menu == "Donde ir - Donde comprar":
    st.title("📍 Donde ir - Donde comprar")
    st.markdown("*Descubre los mejores lugares y negocios de Santa Teresa*")
    
    categorias_neg = ["Todos"] + list(set([n[1] for n in obtener_negocios()[['categoria']].values] if not obtener_negocios().empty else []))
    if len(categorias_neg) > 1:
        filtro_cat = st.selectbox("Filtrar por categoria", categorias_neg)
    else:
        filtro_cat = "Todos"
    
    negocios = obtener_negocios(filtro_cat if filtro_cat != "Todos" else None)
    if not negocios.empty:
        for _, n in negocios.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    if n['imagen_url']:
                        st.image(n['imagen_url'], use_container_width=True)
                    else:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
                with col2:
                    st.markdown(f"### 🏪 {n['nombre']}")
                    st.caption(f"📌 {n['categoria']}")
                    st.write(f"**Reseña:** {n['reseña']}")
                    if n['direccion']:
                        st.write(f"📍 {n['direccion']}")
                    if n['telefono']:
                        st.write(f"📞 {n['telefono']}")
                    if n['horario']:
                        st.write(f"⏰ {n['horario']}")
                st.markdown("---")
    else:
        st.info("No hay negocios agregados aun")

elif menu == "Reflexiones":
    st.title("Reflexiones")
    ref = obtener_reflexion_activa()
    if ref:
        st.markdown(f"### {ref['titulo']}")
        st.write(ref['contenido'])
        st.caption(f"Versiculo: {ref['versiculo']}")
    else:
        st.info("No hay reflexion activa")

elif menu == "Multimedia":
    st.title("Multimedia")
    t1, t2, t3 = st.tabs(["Videos", "Musica", "Radio"])
    
    with t1:
        videos = obtener_videos()
        if not videos.empty:
            for _, v in videos.iterrows():
                st.markdown(f"**{v['titulo']}**")
                mostrar_video(v['video_data'], v['formato'])
                st.caption(f"Subido: {v['fecha_subida']}")
                st.markdown("---")
        else:
            st.info("No hay videos disponibles. Sube videos desde el panel de administrador.")
    
    with t2:
        musicas = obtener_musicas()
        if not musicas.empty:
            for _, m in musicas.iterrows():
                st.markdown(f"**{m['titulo']}**")
                mostrar_musica(m['audio_data'], m['formato'])
                st.caption(f"Agregado: {m['fecha_subida']}")
                st.markdown("---")
        else:
            st.info("No hay musica disponible. Sube musica desde el panel de administrador.")
    
    with t3:
        st.markdown("### Radio Online")
        st.audio("https://streaming.radiosenlinea.net/9090/stream")

elif menu == "Ventana del Pasado":
    st.title("Ventana del Pasado")
    for _, v in obtener_ventana().iterrows():
        st.markdown(f"### {v['titulo']}")
        st.caption(v['fecha_evento'])
        if v['imagen_url']:
            st.image(v['imagen_url'], width=300)
        st.write(v['contenido'])
        st.markdown("---")

elif menu == "Cronicas Reales":
    st.title("Cronicas Reales")
    for _, c in obtener_cronicas().iterrows():
        with st.expander(f"{c['titulo']} - {c['lugar']}"):
            st.write(c['contenido'])
            st.caption(f"Publicado: {c['fecha']}")

elif menu == "Denuncias":
    st.title("Denuncias")
    tab1, tab2 = st.tabs(["Hacer Denuncia", "Ver Denuncias"])
    
    with tab1:
        with st.form("denuncia"):
            nombre = st.text_input("Nombre (opcional)")
            titulo = st.text_input("Titulo")
            desc = st.text_area("Descripcion", height=150)
            ubic = st.text_input("Ubicacion")
            if st.form_submit_button("Enviar"):
                if titulo and desc:
                    guardar_denuncia(nombre, titulo, desc, ubic)
                    st.success("Denuncia enviada!")
    
    with tab2:
        for _, d in obtener_denuncias().iterrows():
            st.markdown(f"**{d['titulo']}** - {d['estatus']}")
            st.caption(d['ubicacion'])

elif menu == "Opiniones":
    st.title("Opiniones")
    tab1, tab2 = st.tabs(["Dar Opinion", "Ver Opiniones"])
    
    with tab1:
        with st.form("opinion"):
            usuario = st.text_input("Nombre")
            comentario = st.text_area("Comentario")
            calif = st.slider("Calificacion", 1, 5, 5)
            if st.form_submit_button("Enviar"):
                if usuario and comentario:
                    guardar_opinion(usuario, comentario, calif)
                    st.success("Opinion enviada!")
    
    with tab2:
        for _, op in obtener_opiniones(aprobadas=True).iterrows():
            estrellas = "⭐" * op['calificacion']
            st.markdown(f"**{op['usuario']}** {estrellas}")
            st.write(op['comentario'])
            st.caption(op['fecha'])

# --- FOOTER ---
st.markdown("""
<div class="bronze-footer">
    <p>⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproduccion total o parcial - Derechos Reservados</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
