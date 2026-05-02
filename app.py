import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text, create_engine
from PIL import Image
import base64
import io
import uuid
import random
import requests
import json

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONEXION A NEON (POSTGRESQL) ---
def init_connection():
    """Inicializa la conexion a la base de datos Neon"""
    try:
        if "DATABASE_URL" in st.secrets:
            conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        elif "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
            conn = st.connection("postgresql", type="sql")
        else:
            st.error("""
            ❌ No se encontro configuracion de base de datos.
            
            Por favor, configura los secrets en Streamlit Cloud:
            
            1. Ve a Settings → Secrets
            2. Agrega:
            
            DATABASE_URL = "postgresql://usuario:contraseña@host/database?sslmode=require"
            """)
            st.stop()
        
        # Probar la conexion
        test_query = conn.query("SELECT 1 as test", ttl=0)
        if test_query.empty:
            st.error("No se pudo verificar la conexion a la base de datos")
            st.stop()
        
        return conn
        
    except Exception as e:
        st.error(f"Error de conexion: {str(e)}")
        st.stop()

conn = init_connection()

# --- CREACION DE TABLAS ---
def create_tables():
    """Crea todas las tablas necesarias si no existen"""
    try:
        with conn.session as s:
            # Tabla de noticias
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                categoria VARCHAR(50),
                contenido TEXT,
                imagen_url TEXT,
                fecha_publicacion VARCHAR(50),
                autor VARCHAR(100),
                visitas INTEGER DEFAULT 0
            )
            """))
            
            # Tabla de reflexiones (Palabra Diaria)
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS reflexiones (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                contenido TEXT,
                autor VARCHAR(100),
                fecha VARCHAR(50),
                activo BOOLEAN DEFAULT TRUE
            )
            """))
            
            # Tabla de Ventana del Pasado
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
            
            # Tabla de Cronicas Reales
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
            
            # Tabla de Denuncias
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
            
            # Tabla de Opiniones
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS opiniones (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(100),
                comentario TEXT,
                calificacion INTEGER,
                fecha VARCHAR(50)
            )
            """))
            
            # Tabla de visitas
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 0,
                ultima_actualizacion VARCHAR(50)
            )
            """))
            
            # Tabla de configuracion (logo, etc.)
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                logo_data TEXT,
                    dolar_bcv REAL DEFAULT 60.0,
                    ultima_actualizacion_dolar VARCHAR(50)
                )
                """))
            
            # Inicializar contador de visitas si no existe
            res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            
            # Inicializar configuracion si no existe
            res_c = s.execute(text("SELECT id FROM configuracion WHERE id = 1")).fetchone()
            if not res_c:
                s.execute(text("INSERT INTO configuracion (id, logo_data, dolar_bcv) VALUES (1, NULL, 60.0)"))
            
            s.commit()
            
    except Exception as e:
        st.error(f"Error al crear las tablas: {str(e)}")
        st.stop()

create_tables()

# --- FUNCIONES DE UTILIDAD ---
def actualizar_contador_visitas():
    """Actualiza el contador global de visitas"""
    try:
        with conn.session as s:
            s.execute(text("UPDATE visitas SET conteo = conteo + 1 WHERE id = 1"))
            s.commit()
    except Exception:
        pass

def obtener_total_visitas():
    """Obtiene el total de visitas de la aplicacion"""
    try:
        res = conn.query("SELECT conteo FROM visitas WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 0
    except Exception:
        return 0

def obtener_precio_dolar():
    """Obtiene el precio del dolar BCV desde la configuracion"""
    try:
        res = conn.query("SELECT dolar_bcv FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty:
            return res.iloc[0,0]
    except Exception:
        pass
    return 60.0

def actualizar_precio_dolar(precio):
    """Actualiza el precio del dolar en la configuracion"""
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET dolar_bcv = :precio, ultima_actualizacion_dolar = :fecha WHERE id = 1"),
                     {"precio": precio, "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")})
            s.commit()
            return True
    except Exception:
        return False

def obtener_logo():
    """Obtiene el logo de la configuracion"""
    try:
        res = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty and res.iloc[0,0]:
            return res.iloc[0,0]
    except Exception:
        pass
    return None

def guardar_logo(logo_b64):
    """Guarda el logo en la configuracion"""
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET logo_data = :logo WHERE id = 1"), {"logo": logo_b64})
            s.commit()
            return True
    except Exception:
        return False

def obtener_efemerides():
    """Obtiene las efemerides del dia actual"""
    hoy = datetime.now()
    dia = hoy.day
    mes = hoy.month
    
    efemerides_db = {
        (1, 1): "Año Nuevo. Fundacion de Santa Teresa del Tuy (1781)",
        (6, 1): "Dia de Reyes Magos",
        (15, 1): "Dia del Maestro",
        (23, 1): "Caida de la Dictadura de Perez Jimenez (1958)",
        (12, 2): "Dia de la Juventud - Batalla de La Victoria (1814)",
        (14, 2): "Dia del Amor y la Amistad",
        (8, 3): "Dia Internacional de la Mujer",
        (19, 3): "Dia de San Jose",
        (19, 4): "Declaracion de la Independencia (1810)",
        (1, 5): "Dia del Trabajador",
        (24, 6): "Batalla de Carabobo - Dia del Ejercito",
        (5, 7): "Firma del Acta de Independencia (1811)",
        (24, 7): "Natalicio de Simon Bolivar",
        (15, 9): "Fundacion de Santa Teresa del Tuy (1781)",
        (12, 10): "Dia de la Resistencia Indigena",
        (2, 11): "Dia de los Difuntos",
        (18, 11): "Dia de la Virgen de Chiquinquira",
        (25, 12): "Navidad",
        (31, 12): "Fin de Año"
    }
    
    efemeride = efemerides_db.get((dia, mes), f"{dia} de {hoy.strftime('%B')} - Un dia especial en la historia")
    return efemeride

def imagen_a_base64(uploaded_file):
    """Convierte una imagen subida a base64"""
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            max_size = (800, 800)
            try:
                img.thumbnail(max_size, Image.LANCZOS)
            except AttributeError:
                img.thumbnail(max_size, Image.ANTIALIAS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70, optimize=True)
            bytes_data = buffer.getvalue()
            return f"data:image/jpeg;base64,{base64.b64encode(bytes_data).decode()}"
        except Exception as e:
            st.error(f"Error al procesar imagen: {e}")
            return None
    return None

# --- SISTEMA DE LOGIN ---
CLAVE_ADMIN = "1966"

def verificar_admin():
    """Verifica si el usuario es administrador"""
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if st.sidebar.checkbox("🔐 Acceso Administrador"):
        clave = st.sidebar.text_input("Clave de Administrador:", type="password")
        if clave == CLAVE_ADMIN:
            st.session_state.autenticado = True
            st.sidebar.success("✅ Acceso concedido")
        elif clave:
            st.sidebar.error("❌ Clave incorrecta")
    
    return st.session_state.autenticado

# --- FUNCIONES CRUD PARA CADA SECCION ---
def publicar_noticia(titulo, categoria, contenido, imagen):
    """Publica una nueva noticia"""
    try:
        imagen_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, imagen_url, fecha_publicacion, autor, visitas)
                VALUES (:t, :c, :cont, :img, :f, :a, 0)
            """), {"t": titulo, "c": categoria, "cont": contenido, "img": imagen_url, 
                   "f": datetime.now().strftime("%d/%m/%Y %H:%M"), "a": "Administrador"})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error al publicar: {e}")
        return False

def obtener_noticias(categoria=None, limite=None):
    """Obtiene noticias de la base de datos"""
    try:
        if categoria and categoria != "Todas":
            query = "SELECT * FROM noticias WHERE categoria = :cat ORDER BY id DESC"
            params = {"cat": categoria}
        else:
            query = "SELECT * FROM noticias ORDER BY id DESC"
            params = {}
        
        if limite:
            query += " LIMIT :lim"
            params["lim"] = limite
        
        df = conn.query(text(query), params=params, ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def eliminar_noticia(noticia_id):
    """Elimina una noticia por ID"""
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM noticias WHERE id = :id"), {"id": noticia_id})
            s.commit()
        return True
    except Exception:
        return False

def guardar_reflexion(titulo, contenido):
    """Guarda una reflexion diaria"""
    try:
        with conn.session as s:
            # Desactivar reflexiones anteriores
            s.execute(text("UPDATE reflexiones SET activo = FALSE"))
            # Insertar nueva reflexion
            s.execute(text("""
                INSERT INTO reflexiones (titulo, contenido, autor, fecha, activo)
                VALUES (:t, :c, :a, :f, TRUE)
            """), {"t": titulo, "c": contenido, "a": "Administrador", "f": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def obtener_reflexion_activa():
    """Obtiene la reflexion activa del dia"""
    try:
        df = conn.query("SELECT * FROM reflexiones WHERE activo = TRUE ORDER BY id DESC LIMIT 1", ttl=0)
        return df.iloc[0] if not df.empty else None
    except Exception:
        return None

def obtener_reflexiones():
    """Obtiene todas las reflexiones"""
    try:
        df = conn.query("SELECT * FROM reflexiones ORDER BY id DESC", ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def guardar_ventana_pasado(titulo, contenido, fecha_evento, imagen):
    """Guarda una entrada en Ventana del Pasado"""
    try:
        imagen_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO ventana_pasado (titulo, contenido, fecha_evento, imagen_url, fecha_publicacion)
                VALUES (:t, :c, :f, :img, :fp)
            """), {"t": titulo, "c": contenido, "f": fecha_evento, "img": imagen_url, 
                   "fp": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def obtener_ventana_pasado(limite=None):
    """Obtiene entradas de Ventana del Pasado"""
    try:
        query = "SELECT * FROM ventana_pasado ORDER BY fecha_evento DESC"
        if limite:
            query += f" LIMIT {limite}"
        df = conn.query(query, ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def guardar_cronica(titulo, contenido, lugar):
    """Guarda una cronica real"""
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO cronicas_reales (titulo, contenido, autor, fecha, lugar)
                VALUES (:t, :c, :a, :f, :l)
            """), {"t": titulo, "c": contenido, "a": "Administrador", 
                   "f": datetime.now().strftime("%d/%m/%Y"), "l": lugar})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def obtener_cronicas():
    """Obtiene todas las cronicas"""
    try:
        df = conn.query("SELECT * FROM cronicas_reales ORDER BY id DESC", ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def guardar_denuncia(denunciante, titulo, descripcion, ubicacion):
    """Guarda una denuncia"""
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO denuncias (denunciante, titulo, descripcion, ubicacion, fecha, estatus)
                VALUES (:d, :t, :desc, :u, :f, 'Pendiente')
            """), {"d": denunciante, "t": titulo, "desc": descripcion, "u": ubicacion, 
                   "f": datetime.now().strftime("%d/%m/%Y")})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def obtener_denuncias(estatus=None):
    """Obtiene denuncias filtradas por estatus"""
    try:
        if estatus and estatus != "Todas":
            df = conn.query("SELECT * FROM denuncias WHERE estatus = :e ORDER BY id DESC", 
                           params={"e": estatus}, ttl=0)
        else:
            df = conn.query("SELECT * FROM denuncias ORDER BY id DESC", ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def actualizar_estatus_denuncia(denuncia_id, nuevo_estatus):
    """Actualiza el estatus de una denuncia"""
    try:
        with conn.session as s:
            s.execute(text("UPDATE denuncias SET estatus = :e WHERE id = :id"), 
                     {"e": nuevo_estatus, "id": denuncia_id})
            s.commit()
        return True
    except Exception:
        return False

def guardar_opinion(usuario, comentario, calificacion):
    """Guarda una opinion de usuario"""
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO opiniones (usuario, comentario, calificacion, fecha)
                VALUES (:u, :c, :cal, :f)
            """), {"u": usuario, "c": comentario, "cal": calificacion, 
                   "f": datetime.now().strftime("%d/%m/%Y %H:%M")})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def obtener_opiniones(limite=20):
    """Obtiene las ultimas opiniones"""
    try:
        df = conn.query("SELECT * FROM opiniones ORDER BY id DESC LIMIT :lim", 
                       params={"lim": limite}, ttl=0)
        return df
    except Exception:
        return pd.DataFrame()

def eliminar_opinion(opinion_id):
    """Elimina una opinion"""
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM opiniones WHERE id = :id"), {"id": opinion_id})
            s.commit()
        return True
    except Exception:
        return False

# --- ESTILOS CSS (VENEZUELA) ---
st.markdown("""
<style>
/* Ocultar elementos de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

/* Fondo tricolor con estrellas */
.stApp {
    background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%);
    background-attachment: fixed;
    position: relative;
}

.stApp::before {
    content: "★ ★ ★ ★ ★ ★ ★ ★ ★ ★";
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    color: rgba(255, 255, 255, 0.05);
    font-size: 30px;
    text-align: center;
    pointer-events: none;
    white-space: pre-wrap;
    line-height: 50px;
    letter-spacing: 20px;
}

/* Contenedor principal para mejor legibilidad */
.main > div {
    background-color: rgba(0, 0, 0, 0.7);
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
}

/* Tarjetas */
.element-container, .stMarkdown, .stAlert, .stInfo {
    background: transparent !important;
}

/* Sidebar semi-transparente */
[data-testid="stSidebar"] {
    background-color: rgba(0, 0, 0, 0.85) !important;
    border-right: 3px solid #FFD700;
}

/* Textos */
h1, h2, h3, h4, .stMarkdown, p, span, label {
    color: #FFFFFF !important;
}

/* Botones */
.stButton > button {
    background: linear-gradient(135deg, #FFD700, #CF142B);
    color: white;
    border: none;
    font-weight: bold;
    transition: transform 0.2s;
}

.stButton > button:hover {
    transform: scale(1.02);
    background: linear-gradient(135deg, #CF142B, #FFD700);
    color: white;
}

/* Inputs */
input, textarea, .stSelectbox, .stDateInput {
    background-color: rgba(255, 255, 255, 0.9) !important;
    color: #000 !important;
    border-radius: 8px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(0, 0, 0, 0.5);
    border-radius: 10px;
    padding: 5px;
}

.stTabs [data-baseweb="tab"] {
    background-color: rgba(0, 0, 0, 0.6);
    border-radius: 8px;
    color: #FFD700 !important;
    font-weight: bold;
    padding: 10px 20px;
}

.stTabs [aria-selected="true"] {
    background-color: #CF142B !important;
    color: white !important;
}

/* Expander */
.streamlit-expanderHeader {
    background-color: rgba(0, 0, 0, 0.6);
    border-radius: 10px;
    border-left: 5px solid #FFD700;
}

/* Tarjeta de noticias */
.noticia-card {
    background: rgba(0, 0, 0, 0.7);
    border-radius: 15px;
    padding: 15px;
    margin-bottom: 20px;
    border-left: 5px solid #FFD700;
}

/* Placa de Bronce - Footer */
.bronze-plaque-footer {
    background: linear-gradient(145deg, #8c6a31, #5d431a);
    border: 5px solid #d4af37;
    padding: 30px 20px;
    border-radius: 15px;
    text-align: center;
    margin-top: 50px;
    margin-bottom: 20px;
    box-shadow: inset 2px 2px 8px rgba(255,255,255,0.3), 10px 10px 25px rgba(0,0,0,0.7);
    position: relative;
    overflow: hidden;
}

.bronze-text-footer {
    color: #ffd700;
    font-family: 'Times New Roman', serif;
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.9);
}

.screw-footer {
    position: absolute;
    width: 18px;
    height: 18px;
    background: radial-gradient(circle at 30% 30%, #999, #333);
    border-radius: 50%;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

.screw-tl-footer { top: 15px; left: 15px; }
.screw-tr-footer { top: 15px; right: 15px; }
.screw-bl-footer { bottom: 15px; left: 15px; }
.screw-br-footer { bottom: 15px; right: 15px; }

/* Panel de administrador */
.admin-panel {
    background: linear-gradient(135deg, #FFD700, #00247D);
    border-radius: 15px;
    padding: 15px;
    margin-bottom: 20px;
}

/* Header venezolano */
.venezuela-header {
    text-align: center;
    padding: 30px;
    background: linear-gradient(135deg, #FFD700 30%, #00247D 50%, #CF142B 70%);
    border-radius: 20px;
    margin-bottom: 30px;
}

.visitas-counter {
    font-size: 2em;
    font-weight: bold;
    color: #FFD700;
    text-align: center;
}

.dolar-price {
    background: rgba(0, 0, 0, 0.6);
    padding: 10px;
    border-radius: 10px;
    text-align: center;
    border: 1px solid #FFD700;
}

/* Reproductor */
.stAudio, .stVideo {
    background: rgba(0, 0, 0, 0.5);
    border-radius: 10px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- ACTUALIZAR CONTADOR DE VISITAS ---
if 'visitado' not in st.session_state:
    actualizar_contador_visitas()
    st.session_state.visitado = True

# --- LOGO Y ENCABEZADO ---
logo_data = obtener_logo()
if logo_data:
    st.markdown(f'<div style="text-align: center;"><img src="{logo_data}" style="max-width: 250px; margin-bottom: -50px;"></div>', unsafe_allow_html=True)

st.markdown('<div class="venezuela-header"><h1>🌟 Santa Teresa al Día 🌟</h1><p>Información, Cultura y Fe para Nuestra Comunidad</p></div>', unsafe_allow_html=True)

# --- SIDEBAR - NAVEGACION PRINCIPAL ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
st.sidebar.title("📋 Menú Principal")

# Opciones del menu
menu_options = [
    "🏠 Portada",
    "📰 Noticias",
    "🙏 Pan de Vida y Reflexiones",
    "🎬 Multimedia",
    "🏪 Guía Comercial",
    "📜 Ventana del Pasado",
    "✍️ Crónicas Reales",
    "⚠️ Denuncias",
    "💬 Opiniones"
]

selected_menu = st.sidebar.radio("Navegación", menu_options)

# --- PANEL DE ADMINISTRACION (SOLO PARA AUTOR) ---
es_admin = verificar_admin()

if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠️ Panel de Control")
    
    admin_action = st.sidebar.selectbox("Acción", [
        "📝 Publicar Noticia",
        "✨ Nueva Reflexión",
        "📜 Agregar a Ventana del Pasado",
        "✍️ Nueva Crónica",
        "⚠️ Gestionar Denuncias",
        "🎨 Configurar Logo",
        "💰 Actualizar Dólar BCV"
    ])
    
    # Admin: Publicar Noticia
    if admin_action == "📝 Publicar Noticia":
        with st.sidebar.expander("✏️ Publicar Nueva Noticia", expanded=True):
            titulo = st.text_input("Título")
            categoria = st.selectbox("Categoría", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=200)
            imagen = st.file_uploader("Imagen (opcional)", type=["jpg", "jpeg", "png"])
            
            if st.button("🚀 Publicar Noticia"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido, imagen):
                        st.success("✅ Noticia publicada exitosamente!")
                        st.rerun()
                    else:
                        st.error("❌ Error al publicar")
                else:
                    st.warning("⚠️ Título y contenido son obligatorios")
    
    # Admin: Nueva Reflexion
    elif admin_action == "✨ Nueva Reflexión":
        with st.sidebar.expander("✏️ Escribir Reflexión Diaria", expanded=True):
            titulo = st.text_input("Título de la Reflexión", value=f"Reflexión del {datetime.now().strftime('%d/%m/%Y')}")
            contenido = st.text_area("Contenido", height=200, placeholder="Escribe la palabra diaria, reflexión o enseñanza...")
            
            if st.button("💾 Guardar Reflexión"):
                if titulo and contenido:
                    if guardar_reflexion(titulo, contenido):
                        st.success("✅ Reflexión guardada como activa!")
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar")
                else:
                    st.warning("⚠️ Título y contenido son obligatorios")
    
    # Admin: Ventana del Pasado
    elif admin_action == "📜 Agregar a Ventana del Pasado":
        with st.sidebar.expander("✏️ Agregar Registro Histórico", expanded=True):
            titulo = st.text_input("Título del Evento")
            fecha_evento = st.text_input("Fecha del Evento", placeholder="Ej: 15 de septiembre de 1781")
            contenido = st.text_area("Descripción Histórica", height=150)
            imagen = st.file_uploader("Imagen (opcional)", type=["jpg", "jpeg", "png"])
            
            if st.button("📜 Guardar Registro"):
                if titulo and contenido:
                    if guardar_ventana_pasado(titulo, contenido, fecha_evento, imagen):
                        st.success("✅ Registro guardado!")
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar")
                else:
                    st.warning("⚠️ Título y contenido son obligatorios")
    
    # Admin: Nueva Cronica
    elif admin_action == "✍️ Nueva Crónica":
        with st.sidebar.expander("✏️ Escribir Crónica", expanded=True):
            titulo = st.text_input("Título")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Crónica", height=150)
            
            if st.button("📖 Guardar Crónica"):
                if titulo and contenido:
                    if guardar_cronica(titulo, contenido, lugar):
                        st.success("✅ Crónica guardada!")
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar")
                else:
                    st.warning("⚠️ Título y contenido son obligatorios")
    
    # Admin: Gestionar Denuncias
    elif admin_action == "⚠️ Gestionar Denuncias":
        with st.sidebar.expander("📋 Gestionar Denuncias", expanded=True):
            denuncias_df = obtener_denuncias()
            if not denuncias_df.empty:
                for _, den in denuncias_df.iterrows():
                    st.markdown(f"**ID:** {den['id']} | **Estado:** {den['estatus']}")
                    st.markdown(f"**{den['titulo']}** - {den['denunciante']}")
                    with st.expander(f"Ver detalles - {den['titulo']}"):
                        st.write(f"**Descripción:** {den['descripcion']}")
                        st.write(f"**Ubicación:** {den['ubicacion']}")
                        st.write(f"**Fecha:** {den['fecha']}")
                        nuevo_estado = st.selectbox(
                            "Cambiar estado",
                            ["Pendiente", "En revisión", "Resuelta", "Descartada"],
                            key=f"estado_{den['id']}"
                        )
                        if st.button(f"Actualizar", key=f"btn_{den['id']}"):
                            if actualizar_estatus_denuncia(den['id'], nuevo_estado):
                                st.success("Estado actualizado")
                                st.rerun()
            else:
                st.info("No hay denuncias registradas")
    
    # Admin: Configurar Logo
    elif admin_action == "🎨 Configurar Logo":
        with st.sidebar.expander("🎨 Configurar Logo", expanded=True):
            st.write("**Logo actual:**")
            if logo_data:
                st.image(logo_data, width=150)
                if st.button("🗑️ Eliminar Logo"):
                    if guardar_logo(None):
                        st.success("Logo eliminado")
                        st.rerun()
            else:
                st.info("No hay logo configurado")
            
            st.markdown("---")
            nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg", "jpeg"])
            if nuevo_logo and st.button("💾 Guardar Logo"):
                logo_b64 = imagen_a_base64(nuevo_logo)
                if logo_b64:
                    if guardar_logo(logo_b64):
                        st.success("Logo guardado correctamente")
                        st.rerun()
                    else:
                        st.error("Error al guardar")
    
    # Admin: Actualizar Dolar BCV
    elif admin_action == "💰 Actualizar Dólar BCV":
        with st.sidebar.expander("💰 Actualizar Precio del Dólar", expanded=True):
            precio_actual = obtener_precio_dolar()
            st.write(f"**Precio actual:** {precio_actual:.2f} Bs/USD")
            nuevo_precio = st.number_input("Nuevo precio (Bs/USD)", min_value=0.0, step=0.01, value=float(precio_actual))
            if st.button("💾 Actualizar"):
                if actualizar_precio_dolar(nuevo_precio):
                    st.success(f"Precio actualizado a {nuevo_precio:.2f} Bs/USD")
                    st.rerun()
                else:
                    st.error("Error al actualizar")

# --- CONTENIDO PRINCIPAL SEGUN SELECCION ---

# 1. PORTADA
if selected_menu == "🏠 Portada":
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📅 Fecha y Hora")
        ahora = datetime.now()
        fecha_actual = ahora.strftime("%A, %d de %B de %Y")
        hora_actual = ahora.strftime("%I:%M:%S %p")
        st.markdown(f"**{fecha_actual}**")
        st.markdown(f"**⏰ {hora_actual}**")
        
        st.markdown("---")
        st.markdown("### 📜 Efemérides del Día")
        efemeride = obtener_efemerides()
        st.info(f"📖 {efemeride}")
    
    with col2:
        total_visitas = obtener_total_visitas()
        precio_dolar = obtener_precio_dolar()
        st.markdown(f"""
        <div class="visitas-counter">
            👥 {total_visitas:,}
        </div>
        <div class="dolar-price">
            💵 Dólar BCV: <b>{precio_dolar:.2f} Bs</b>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📰 Últimas Noticias")
    
    ultimas_noticias = obtener_noticias(limite=3)
    if not ultimas_noticias.empty:
        for _, noticia in ultimas_noticias.iterrows():
            with st.container():
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if noticia['imagen_url']:
                        st.image(noticia['imagen_url'], use_container_width=True)
                with col_b:
                    st.markdown(f"**{noticia['titulo']}**")
                    st.caption(f"📅 {noticia['fecha_publicacion']} | 🏷️ {noticia['categoria']}")
                    st.write(noticia['contenido'][:200] + "..." if len(noticia['contenido']) > 200 else noticia['contenido'])
                st.markdown("---")
    else:
        st.info("No hay noticias publicadas aún")

# 2. NOTICIAS
elif selected_menu == "📰 Noticias":
    st.markdown("## 📰 Sección de Noticias")
    
    col_filtro, col_accion = st.columns([2, 1])
    with col_filtro:
        categoria_filtro = st.selectbox("Filtrar por categoría", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    
    noticias_df = obtener_noticias(categoria=categoria_filtro if categoria_filtro != "Todas" else None)
    
    if not noticias_df.empty:
        for _, noticia in noticias_df.iterrows():
            with st.container():
                col_img, col_text = st.columns([1, 2])
                with col_img:
                    if noticia['imagen_url']:
                        st.image(noticia['imagen_url'], use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=Sin+Imagen", use_container_width=True)
                with col_text:
                    st.markdown(f"### {noticia['titulo']}")
                    st.caption(f"📅 {noticia['fecha_publicacion']} | 🏷️ {noticia['categoria']} | 👁️ {noticia['visitas']} visitas")
                    st.write(noticia['contenido'])
                
                if es_admin:
                    if st.button(f"🗑️ Eliminar", key=f"del_not_{noticia['id']}"):
                        if eliminar_noticia(noticia['id']):
                            st.success("Noticia eliminada")
                            st.rerun()
                st.markdown("---")
    else:
        st.info("No hay noticias en esta categoría")

# 3. PAN DE VIDA Y REFLEXIONES
elif selected_menu == "🙏 Pan de Vida y Reflexiones":
    st.markdown("## 🙏 Pan de Vida y Reflexiones")
    
    reflexion_activa = obtener_reflexion_activa()
    
    if reflexion_activa is not None:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FFD70020, #00247D20); padding: 25px; border-radius: 15px; border-left: 8px solid #FFD700;">
            <h2 style="color: #FFD700; text-align: center;">✨ {reflexion_activa['titulo']} ✨</h2>
            <p style="font-size: 1.2em; text-align: center;">{reflexion_activa['contenido']}</p>
            <p style="text-align: right; margin-top: 20px;"><i>— {reflexion_activa['autor']}, {reflexion_activa['fecha']}</i></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No hay reflexión activa para hoy")
    
    if es_admin:
        st.markdown("---")
        st.markdown("### 📜 Reflexiones Anteriores")
        reflexiones_anteriores = obtener_reflexiones()
        if not reflexiones_anteriores.empty:
            for _, ref in reflexiones_anteriores.iterrows():
                with st.expander(f"{ref['titulo']} - {ref['fecha']}"):
                    st.write(ref['contenido'])
        else:
            st.info("No hay reflexiones anteriores")

# 4. MULTIMEDIA
elif selected_menu == "🎬 Multimedia":
    st.markdown("## 🎬 Multimedia")
    
    tab_video, tab_audio, tab_radio = st.tabs(["🎥 Videos", "🎵 Música", "📻 Radio Online"])
    
    with tab_video:
        st.markdown("### 📺 Videos Destacados")
        
        video_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=3Yh_6_zItPU"
        ]
        
        for i, url in enumerate(video_urls):
            st.video(url)
            if es_admin:
                if st.button(f"🗑️ Eliminar Video {i+1}"):
                    st.warning("Función en desarrollo")
    
    with tab_audio:
        st.markdown("### 🎵 Música para Disfrutar")
        
        audio_file = st.file_uploader("Subir audio (MP3)", type=["mp3"], key="audio_upload")
        if audio_file:
            st.audio(audio_file, format="audio/mp3")
            if es_admin:
                st.success("Audio cargado temporalmente")
    
    with tab_radio:
        st.markdown("### 📻 Radio Online")
        st.markdown("**Escucha nuestra radio en vivo**")
        st.audio("https://streaming.listen2myradio.com/example", format="audio/mp3")
        st.caption("Radio Santa Teresa - 24/7 al aire")

# 5. GUIA COMERCIAL
elif selected_menu == "🏪 Guía Comercial":
    st.markdown("## 🏪 Guía Comercial de Santa Teresa")
    
    st.info("🔗 **Acceso a la Guía Comercial**")
    
    st.markdown("""
    <div style="text-align: center; padding: 30px; background: rgba(0,0,0,0.5); border-radius: 15px;">
        <h3>📱 Guía Comercial Almenar</h3>
        <p>Encuentra comercios, servicios y promociones en Santa Teresa del Tuy</p>
        <a href="https://guia-comercial-almenar.streamlit.app" target="_blank">
            <button style="background: linear-gradient(135deg, #FFD700, #CF142B); 
                           color: white; border: none; padding: 15px 30px; 
                           border-radius: 10px; font-size: 1.2em; cursor: pointer;">
                🌐 Ir a la Guía Comercial
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Integracion de la app externa via iframe
    st.markdown("---")
    st.markdown("### Vista previa de la Guía Comercial")
    st.components.v1.iframe("https://guia-comercial-almenar.streamlit.app", height=600, scrolling=True)

# 6. VENTANA DEL PASADO
elif selected_menu == "📜 Ventana del Pasado":
    st.markdown("## 📜 Ventana del Pasado")
    st.markdown("*Recordar es vivir... Viajemos a través de la historia de Santa Teresa*")
    
    ventana_df = obtener_ventana_pasado(limite=20)
    
    if not ventana_df.empty:
        for _, registro in ventana_df.iterrows():
            with st.container():
                col_hist_img, col_hist_text = st.columns([1, 2])
                with col_hist_img:
                    if registro['imagen_url']:
                        st.image(registro['imagen_url'], use_container_width=True)
                with col_hist_text:
                    st.markdown(f"### 🏛️ {registro['titulo']}")
                    st.caption(f"📅 {registro['fecha_evento']}")
                    st.write(registro['contenido'])
                st.markdown("---")
    else:
        st.info("Próximamente más contenido histórico")

# 7. CRONICAS REALES
elif selected_menu == "✍️ Crónicas Reales":
    st.markdown("## ✍️ Crónicas Reales")
    st.markdown("*Historias y testimonios de nuestra gente*")
    
    cronicas_df = obtener_cronicas()
    
    if not cronicas_df.empty:
        for _, cronica in cronicas_df.iterrows():
            with st.expander(f"📖 {cronica['titulo']} - {cronica['lugar']} ({cronica['fecha']})"):
                st.write(cronica['contenido'])
                st.caption(f"Publicado por: {cronica['autor']}")
    else:
        st.info("No hay crónicas publicadas aún")

# 8. DENUNCIAS
elif selected_menu == "⚠️ Denuncias":
    st.markdown("## ⚠️ Sección de Denuncias Ciudadanas")
    st.markdown("*Todas las denuncias son anónimas y serán investigadas*")
    
    tab_denunciar, tab_ver_denuncias = st.tabs(["📝 Hacer Denuncia", "📋 Ver Denuncias"])
    
    with tab_denunciar:
        with st.form("form_denuncia_ciudadana"):
            denunciante = st.text_input("Tu nombre (puede ser anónimo)", placeholder="Anónimo o nombre real")
            titulo_den = st.text_input("Título de la denuncia")
            descripcion_den = st.text_area("Descripción detallada", height=150)
            ubicacion_den = st.text_input("Ubicación del hecho")
            
            if st.form_submit_button("🚨 Enviar Denuncia"):
                if titulo_den and descripcion_den:
                    if guardar_denuncia(denunciante or "Anónimo", titulo_den, descripcion_den, ubicacion_den):
                        st.success("✅ Denuncia enviada. Las autoridades la revisarán.")
                        st.balloons()
                    else:
                        st.error("❌ Error al enviar")
                else:
                    st.warning("⚠️ Título y descripción son obligatorios")
    
    with tab_ver_denuncias:
        estatus_filtro = st.selectbox("Filtrar por estado", ["Todas", "Pendiente", "En revisión", "Resuelta", "Descartada"])
        denuncias_mostrar = obtener_denuncias(estatus=estatus_filtro if estatus_filtro != "Todas" else None)
        
        if not denuncias_mostrar.empty:
            for _, den in denuncias_mostrar.iterrows():
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <strong>📌 {den['titulo']}</strong><br>
                    <span style="color: #FFD700;">Estado: {den['estatus']}</span><br>
                    <small>📍 {den['ubicacion']} | 📅 {den['fecha']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay denuncias para mostrar")

# 9. OPINIONES
elif selected_menu == "💬 Opiniones":
    st.markdown("## 💬 Opiniones de Nuestros Visitantes")
    
    tab_opinar, tab_ver_opiniones, tab_admin_opiniones = st.tabs(["💭 Dar Opinión", "📖 Ver Opiniones", "🛠️ Administrar (Autor)"])
    
    with tab_opinar:
        with st.form("form_opinion"):
            usuario = st.text_input("Tu nombre")
            comentario = st.text_area("Tu opinión", height=100)
            calificacion = st.slider("Calificación", 1, 5, 5, help="1 = Muy malo, 5 = Excelente")
            
            if st.form_submit_button("Enviar Opinión"):
                if usuario and comentario:
                    if guardar_opinion(usuario, comentario, calificacion):
                        st.success("✅ Gracias por tu opinión!")
                        st.balloons()
                    else:
                        st.error("❌ Error al enviar")
                else:
                    st.warning("⚠️ Nombre y comentario son obligatorios")
    
    with tab_ver_opiniones:
        opiniones_df = obtener_opiniones(limite=50)
        if not opiniones_df.empty:
            for _, op in opiniones_df.iterrows():
                estrellas = "⭐" * op['calificacion'] + "☆" * (5 - op['calificacion'])
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                    <strong>{op['usuario']}</strong> {estrellas}<br>
                    {op['comentario']}<br>
                    <small style="color: #ccc;">📅 {op['fecha']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay opiniones aún. ¡Sé el primero en opinar!")
    
    with tab_admin_opiniones:
        if es_admin:
            st.markdown("### Administrar Opiniones")
            opiniones_admin = obtener_opiniones(limite=100)
            if not opiniones_admin.empty:
                for _, op in opiniones_admin.iterrows():
                    col_op, col_btn = st.columns([4, 1])
                    with col_op:
                        st.write(f"**{op['usuario']}** (⭐{op['calificacion']}): {op['comentario']}")
                        st.caption(op['fecha'])
                    with col_btn:
                        if st.button("🗑️", key=f"del_opinion_{op['id']}"):
                            if eliminar_opinion(op['id']):
                                st.success("Opinión eliminada")
                                st.rerun()
                    st.markdown("---")
            else:
                st.info("No hay opiniones para administrar")
        else:
            st.warning("Acceso restringido al autor")

# --- FOOTER - PLACA DE BRONCE ---
st.markdown("""
<div class="bronze-plaque-footer">
    <div class="screw-footer screw-tl-footer"></div>
    <div class="screw-footer screw-tr-footer"></div>
    <div class="screw-footer screw-bl-footer"></div>
    <div class="screw-footer screw-br-footer"></div>
    <div class="bronze-text-footer">
        <span style="font-size: 1.5em;">⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</span><br><br>
        <span style="font-size: 1.1em;">Prohibida la reproducción total o parcial</span><br>
        <span style="font-size: 1.3em; letter-spacing: 4px; display: block; margin: 10px 0;">DERECHOS RESERVADOS</span>
        <span style="font-size: 1.2em;">Santa Teresa del Tuy, 2.026</span>
    </div>
</div>
""", unsafe_allow_html=True)
