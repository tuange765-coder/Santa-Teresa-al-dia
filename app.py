import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import io
import uuid
import random

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
                autor VARCHAR(100)
            )
            """))
            
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
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS ventana_pasado (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(255),
                contenido TEXT,
                fecha_evento VARCHAR(50)
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
                fecha VARCHAR(50)
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
                dolar_bcv REAL DEFAULT 60.0
            )
            """))
            
            res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if not res_v:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            
            res_c = s.execute(text("SELECT id FROM configuracion WHERE id = 1")).fetchone()
            if not res_c:
                s.execute(text("INSERT INTO configuracion (id, logo_data, dolar_bcv) VALUES (1, NULL, 60.0)"))
            
            s.commit()
    except Exception as e:
        st.error(f"Error al crear tablas: {str(e)}")

create_tables()

# --- NOTICIAS DIARIAS AUTOMATICAS (CORREGIDO) ---
def cargar_noticias_diarias():
    """Carga noticias predeterminadas si no hay noticias en la base de datos"""
    try:
        noticias_existentes = obtener_noticias()
        if noticias_existentes.empty:
            noticias_default = [
                {
                    "titulo": "🌞 Buenos días Santa Teresa",
                    "categoria": "Nacional",
                    "contenido": "Hoy amanece con un clima cálido en nuestra ciudad. La temperatura rondará los 28°C. ¡Aprovecha el día!",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "🚧 Reporte de Vialidad",
                    "categoria": "Nacional",
                    "contenido": "Se reporta tránsito fluido en la Autopista Regional del Centro. Se recomienda precaución en el sector de La Yaguara.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "⚽ Deportes",
                    "categoria": "Deportes",
                    "contenido": "La selección venezolana se prepara para su próximo encuentro. Los jugadores entrenan a full.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "🌍 Internacional",
                    "categoria": "Internacional",
                    "contenido": "Noticias importantes desde el mundo. Mantente informado con Santa Teresa al Día.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "📢 Reportaje del Día",
                    "categoria": "Reportajes",
                    "contenido": "Conoce la historia de los emprendedores de Santa Teresa que están transformando nuestra comunidad.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                }
            ]
            
            with conn.session as s:
                for n in noticias_default:
                    s.execute(text("""
                        INSERT INTO noticias (titulo, categoria, contenido, fecha_publicacion, autor)
                        VALUES (:t, :c, :cont, :f, 'Santa Teresa al Día')
                    """), {"t": n["titulo"], "c": n["categoria"], "cont": n["contenido"], "f": n["fecha"]})
                s.commit()
    except Exception as e:
        st.warning(f"No se pudieron cargar noticias automáticas: {e}")

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

def obtener_precio_dolar():
    try:
        res = conn.query("SELECT dolar_bcv FROM configuracion WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 60.0
    except:
        return 60.0

def actualizar_precio_dolar(precio):
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET dolar_bcv = :p WHERE id = 1"), {"p": precio})
            s.commit()
            return True
    except:
        return False

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
    hoy = datetime.now()
    dia = hoy.day
    mes = hoy.month
    efemerides = {
        (1,1): "Año Nuevo - Fundacion de Santa Teresa del Tuy (1781)",
        (19,4): "Declaracion de la Independencia (1810)",
        (24,6): "Batalla de Carabobo - Dia del Ejercito",
        (5,7): "Firma del Acta de Independencia (1811)",
        (24,7): "Natalicio del Libertador Simon Bolivar",
        (12,10): "Dia de la Resistencia Indigena",
        (25,12): "Navidad - Nacimiento del Niño Jesus"
    }
    return efemerides.get((dia, mes), f"{dia} de {hoy.strftime('%B')}")

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

# --- FUNCIONES NOTICIAS ---
def publicar_noticia(titulo, categoria, contenido, imagen):
    try:
        img_url = imagen_a_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, imagen_url, fecha_publicacion, autor)
                VALUES (:t, :c, :cont, :img, :f, :a)
            """), {"t": titulo, "c": categoria, "cont": contenido, "img": img_url,
                   "f": datetime.now().strftime("%d/%m/%Y"), "a": "Admin"})
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

# --- FUNCIONES REFLEXIONES ---
def guardar_reflexion(titulo, contenido):
    try:
        with conn.session as s:
            s.execute(text("UPDATE reflexiones SET activo = FALSE"))
            s.execute(text("""
                INSERT INTO reflexiones (titulo, contenido, autor, fecha, activo)
                VALUES (:t, :c, :a, :f, TRUE)
            """), {"t": titulo, "c": contenido, "a": "Admin", "f": datetime.now().strftime("%d/%m/%Y")})
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

# --- FUNCIONES VENTANA PASADO ---
def guardar_ventana(titulo, contenido, fecha_evento):
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO ventana_pasado (titulo, contenido, fecha_evento)
                VALUES (:t, :c, :f)
            """), {"t": titulo, "c": contenido, "f": fecha_evento})
            s.commit()
        return True
    except:
        return False

def obtener_ventana():
    try:
        return conn.query("SELECT * FROM ventana_pasado ORDER BY fecha_evento DESC", ttl=0)
    except:
        return pd.DataFrame()

# --- FUNCIONES CRONICAS ---
def guardar_cronica(titulo, contenido, lugar):
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO cronicas_reales (titulo, contenido, autor, fecha, lugar)
                VALUES (:t, :c, :a, :f, :l)
            """), {"t": titulo, "c": contenido, "a": "Admin", "f": datetime.now().strftime("%d/%m/%Y"), "l": lugar})
            s.commit()
        return True
    except:
        return False

def obtener_cronicas():
    try:
        return conn.query("SELECT * FROM cronicas_reales ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

# --- FUNCIONES DENUNCIAS ---
def guardar_denuncia(denunciante, titulo, descripcion, ubicacion):
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO denuncias (denunciante, titulo, descripcion, ubicacion, fecha, estatus)
                VALUES (:d, :t, :desc, :u, :f, 'Pendiente')
            """), {"d": denunciante or "Anonimo", "t": titulo, "desc": descripcion, 
                   "u": ubicacion, "f": datetime.now().strftime("%d/%m/%Y")})
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
        with conn.session as s:
            s.execute(text("""
                INSERT INTO opiniones (usuario, comentario, calificacion, fecha)
                VALUES (:u, :c, :cal, :f)
            """), {"u": usuario, "c": comentario, "cal": calificacion, 
                   "f": datetime.now().strftime("%d/%m/%Y %H:%M")})
            s.commit()
        return True
    except:
        return False

def obtener_opiniones():
    try:
        return conn.query("SELECT * FROM opiniones ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def eliminar_opinion(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM opiniones WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- CARGAR NOTICIAS DIARIAS AL INICIAR (CORREGIDO) ---
cargar_noticias_diarias()

# --- ESTILOS CSS MEJORADOS ---
st.markdown("""
<style>
/* Fondo tricolor con estrellas */
.stApp {
    background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%);
    background-attachment: fixed;
    position: relative;
}

/* Estrellas de la bandera */
.stApp::before {
    content: "★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★";
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    color: rgba(255, 255, 255, 0.12);
    font-size: 35px;
    text-align: center;
    pointer-events: none;
    white-space: pre-wrap;
    line-height: 60px;
    letter-spacing: 25px;
}

/* Contenido principal */
.main > div {
    background-color: rgba(0, 0, 0, 0.65);
    border-radius: 20px;
    padding: 20px;
    margin: 10px 0;
    backdrop-filter: blur(2px);
}

/* Sidebar venezolano */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(0,0,0,0.9) 0%, rgba(0,36,125,0.95) 50%, rgba(207,20,43,0.95) 100%) !important;
    border-right: 3px solid #FFD700;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

/* Títulos */
h1, h2, h3, h4 {
    color: #FFD700 !important;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

p, span, label {
    color: #FFFFFF !important;
}

/* Botones */
.stButton > button {
    background: linear-gradient(135deg, #FFD700, #CF142B);
    color: white !important;
    border: none;
    font-weight: bold;
    border-radius: 25px;
    padding: 8px 20px;
    transition: all 0.3s;
}

.stButton > button:hover {
    transform: scale(1.02);
    background: linear-gradient(135deg, #CF142B, #FFD700);
    box-shadow: 0 0 15px rgba(255,215,0,0.5);
}

/* Inputs */
input, textarea, .stSelectbox {
    background-color: rgba(255, 255, 255, 0.95) !important;
    color: #000000 !important;
    border-radius: 12px;
    border: 2px solid #FFD700 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(0, 0, 0, 0.5);
    border-radius: 15px;
    padding: 5px;
}

.stTabs [data-baseweb="tab"] {
    background-color: rgba(0, 0, 0, 0.7);
    border-radius: 12px;
    color: #FFD700 !important;
    font-weight: bold;
    padding: 12px 25px;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #FFD700, #CF142B) !important;
    color: white !important;
}

/* Panel de estadisticas */
.stats-panel {
    background: rgba(0, 0, 0, 0.6);
    padding: 15px;
    border-radius: 20px;
    border: 2px solid #FFD700;
    text-align: center;
    margin-bottom: 20px;
}

/* Footer - Placa de Bronce */
.bronze-footer {
    background: linear-gradient(145deg, #8c6a31, #5d431a);
    border: 5px solid #d4af37;
    padding: 25px;
    border-radius: 20px;
    text-align: center;
    margin-top: 50px;
    position: relative;
}

.bronze-footer p {
    color: #ffd700 !important;
    font-family: 'Times New Roman', serif;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --- CONTADOR DE VISITAS ---
if 'visitado' not in st.session_state:
    actualizar_contador()
    st.session_state.visitado = True

# --- ENCABEZADO ---
st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <div style="background: linear-gradient(135deg, #FFD700, #00247D, #CF142B); 
                border-radius: 20px; padding: 20px;">
        <h1 style="color: white; text-shadow: 3px 3px 6px black;">🌟 Santa Teresa al Día 🌟</h1>
        <p style="color: white; font-size: 1.2em;">Información, Cultura y Fe para Nuestra Comunidad</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style="text-align: center;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png" 
             style="width: 150px; border-radius: 15px; border: 2px solid #FFD700;">
        <h2 style="color: #FFD700; margin-top: 10px;">Santa Teresa</h2>
        <p style="color: white;">"Tierra de Gracia"</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    menu = st.radio("📋 Menú Principal", [
        "🏠 Portada", "📰 Noticias", "🙏 Reflexiones", "🎬 Multimedia",
        "🏪 Guía Comercial", "📜 Ventana del Pasado", "✍️ Crónicas Reales",
        "⚠️ Denuncias", "💬 Opiniones"
    ], index=0)
    
    st.markdown("---")
    
    # Login Admin
    es_admin = False
    with st.expander("🔐 Administrador", expanded=False):
        clave = st.text_input("Clave:", type="password")
        if clave == "Juan*316*" or clave == "1966":
            es_admin = True
            st.success("✅ Acceso concedido")
        elif clave:
            st.error("❌ Clave incorrecta")

# --- PANEL DE ADMINISTRACION ---
if es_admin:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🛠️ Panel de Control")
        admin_accion = st.selectbox("Acción", [
            "📝 Publicar Noticia", "✨ Nueva Reflexión", "📜 Agregar a Ventana",
            "✍️ Nueva Crónica", "⚠️ Gestionar Denuncias", "🎨 Configurar App"
        ])
    
    if admin_accion == "📝 Publicar Noticia":
        with st.expander("📝 Publicar Nueva Noticia", expanded=True):
            titulo = st.text_input("Título")
            categoria = st.selectbox("Categoría", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=150)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.button("📢 Publicar"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido, imagen):
                        st.success("✅ Noticia publicada!")
                        st.rerun()
                    else:
                        st.error("❌ Error al publicar")
                else:
                    st.warning("⚠️ Completa los campos")
    
    elif admin_accion == "✨ Nueva Reflexión":
        with st.expander("✨ Escribir Reflexión", expanded=True):
            titulo = st.text_input("Título", value=f"Reflexión del {datetime.now().strftime('%d/%m/%Y')}")
            contenido = st.text_area("Contenido", height=150)
            if st.button("💾 Guardar"):
                if titulo and contenido:
                    if guardar_reflexion(titulo, contenido):
                        st.success("✅ Reflexión guardada!")
                        st.rerun()
    
    elif admin_accion == "📜 Agregar a Ventana":
        with st.expander("📜 Nuevo Registro Histórico", expanded=True):
            titulo = st.text_input("Título")
            fecha = st.text_input("Fecha", placeholder="Ej: 15 de septiembre de 1781")
            contenido = st.text_area("Descripción", height=150)
            if st.button("📜 Guardar"):
                if titulo and contenido:
                    if guardar_ventana(titulo, contenido, fecha):
                        st.success("✅ Registro guardado!")
                        st.rerun()
    
    elif admin_accion == "✍️ Nueva Crónica":
        with st.expander("✍️ Nueva Crónica", expanded=True):
            titulo = st.text_input("Título")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Crónica", height=150)
            if st.button("📖 Guardar"):
                if titulo and contenido:
                    if guardar_cronica(titulo, contenido, lugar):
                        st.success("✅ Crónica guardada!")
                        st.rerun()
    
    elif admin_accion == "⚠️ Gestionar Denuncias":
        st.write("### Gestión de Denuncias")
        denuncias = obtener_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                with st.expander(f"📌 {d['titulo']} - {d['estatus']}"):
                    st.write(f"**Denunciante:** {d['denunciante']}")
                    st.write(f"**Descripción:** {d['descripcion']}")
                    st.write(f"**Ubicación:** {d['ubicacion']}")
                    st.write(f"**Fecha:** {d['fecha']}")
                    nuevo_estado = st.selectbox("Estado", ["Pendiente", "En revisión", "Resuelta", "Descartada"], 
                                               key=f"est_{d['id']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Actualizar", key=f"upd_{d['id']}"):
                            actualizar_estatus_denuncia(d['id'], nuevo_estado)
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Eliminar", key=f"del_{d['id']}"):
                            eliminar_denuncia(d['id'])
                            st.rerun()
        else:
            st.info("No hay denuncias registradas")
    
    elif admin_accion == "🎨 Configurar App":
        st.write("### Configuración de la App")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**💰 Precio del Dólar BCV**")
            precio_actual = obtener_precio_dolar()
            nuevo_precio = st.number_input("Precio (Bs/USD)", value=precio_actual, step=0.01)
            if st.button("Actualizar Dólar"):
                if actualizar_precio_dolar(nuevo_precio):
                    st.success("✅ Precio actualizado!")
                    st.rerun()
        
        with col2:
            st.write("**🎨 Logo de la App**")
            logo_actual = obtener_logo()
            if logo_actual:
                st.image(logo_actual, width=100)
            nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg"])
            if nuevo_logo and st.button("Guardar Logo"):
                logo_b64 = imagen_a_base64(nuevo_logo)
                if guardar_logo(logo_b64):
                    st.success("✅ Logo guardado!")
                    st.rerun()

# --- PANEL SUPERIOR ---
ahora = datetime.now()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

visitas = obtener_visitas()
precio_dolar = obtener_precio_dolar()
efemeride = obtener_efemerides()

st.markdown(f"""
<div class="stats-panel">
    <span style="color: #FFD700; font-size: 1.2em;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color: white; font-size: 1.8em; font-weight: bold;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 {visitas:,} visitas | 💵 {precio_dolar:.2f} Bs/USD</span>
</div>

<div style="background: linear-gradient(135deg, #1a3a5c, #0a1a3a); padding: 15px; border-radius: 15px; border-left: 5px solid #FFD700; margin-bottom: 20px;">
    <span style="color: #FFD700; font-weight: bold;">📅 EFEMÉRIDES DEL DÍA</span><br>
    <span style="color: white;">{efemeride}</span>
</div>
""", unsafe_allow_html=True)

# --- CONTENIDO PRINCIPAL ---
if menu == "🏠 Portada":
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1>⭐ Santa Teresa al Día ⭐</h1>
        <p style="font-size: 1.2em;">Bienvenidos a tu fuente de información confiable</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📰 Últimas Noticias")
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.head(4).iterrows():
            with st.container():
                st.markdown(f"**📌 {n['titulo']}**")
                st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
                st.write(n['contenido'][:200] + "..." if len(n['contenido']) > 200 else n['contenido'])
                st.markdown("---")
    else:
        st.info("No hay noticias disponibles")

elif menu == "📰 Noticias":
    st.title("📰 Noticias")
    
    categoria = st.selectbox("Filtrar por categoría", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    
    noticias = obtener_noticias(categoria if categoria != "Todas" else None)
    
    if not noticias.empty:
        for _, n in noticias.iterrows():
            with st.container():
                st.markdown(f"### {n['titulo']}")
                st.caption(f"📅 {n['fecha_publicacion']} | 🏷️ {n['categoria']}")
                st.write(n['contenido'])
                if es_admin:
                    if st.button("🗑️ Eliminar", key=f"del_{n['id']}"):
                        eliminar_noticia(n['id'])
                        st.rerun()
                st.markdown("---")
    else:
        st.info("No hay noticias en esta categoría")

elif menu == "🙏 Reflexiones":
    st.title("🙏 Pan de Vida y Reflexiones")
    
    reflexion = obtener_reflexion_activa()
    if reflexion is not None:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0,0,0,0.6), rgba(0,36,125,0.6)); 
                    padding: 35px; border-radius: 20px; border-left: 8px solid #FFD700; text-align: center;">
            <h2 style="color: #FFD700;">✨ {reflexion['titulo']} ✨</h2>
            <p style="font-size: 1.3em;">{reflexion['contenido']}</p>
            <p style="margin-top: 20px;"><i>— {reflexion['autor']}, {reflexion['fecha']}</i></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No hay reflexión activa para hoy")
    
    if es_admin:
        st.markdown("---")
        st.markdown("### Reflexiones Anteriores")
        reflexiones = obtener_reflexiones()
        for _, r in reflexiones.iterrows():
            with st.expander(f"{r['titulo']} - {r['fecha']}"):
                st.write(r['contenido'])

elif menu == "🎬 Multimedia":
    st.title("🎬 Multimedia")
    tab1, tab2, tab3 = st.tabs(["🎥 Videos", "🎵 Música", "📻 Radio"])
    with tab1:
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    with tab2:
        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    with tab3:
        st.audio("https://streaming.listen2myradio.com/example")

elif menu == "🏪 Guía Comercial":
    st.title("🏪 Guía Comercial de Santa Teresa")
    st.markdown("""
    <div style="text-align: center; padding: 50px; background: rgba(0,0,0,0.5); border-radius: 25px;">
        <h2 style="color: #FFD700;">📱 Guía Comercial Almenar</h2>
        <p>Encuentra comercios, servicios y promociones en Santa Teresa del Tuy</p>
        <a href="https://williantuguiasantateresa.streamlit.app" target="_blank">
            <button style="background: linear-gradient(135deg, #FFD700, #CF142B); 
                           padding: 15px 35px; border-radius: 30px; border: none; 
                           color: white; font-size: 1.2em; cursor: pointer; margin-top: 20px;">
                🌐 Ir a la Guía Comercial
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

elif menu == "📜 Ventana del Pasado":
    st.title("📜 Ventana del Pasado")
    st.markdown("*Recordar es vivir... Viajemos a través de la historia de Santa Teresa*")
    
    registros = obtener_ventana()
    if not registros.empty:
        for _, r in registros.iterrows():
            st.markdown(f"### 🏛️ {r['titulo']}")
            st.caption(f"📅 {r['fecha_evento']}")
            st.write(r['contenido'])
            st.markdown("---")
    else:
        st.info("Próximamente más contenido histórico")

elif menu == "✍️ Crónicas Reales":
    st.title("✍️ Crónicas Reales")
    st.markdown("*Historias y testimonios de nuestra gente*")
    
    cronicas = obtener_cronicas()
    if not cronicas.empty:
        for _, c in cronicas.iterrows():
            with st.expander(f"📖 {c['titulo']} - {c['lugar']} ({c['fecha']})"):
                st.write(c['contenido'])
                st.caption(f"Publicado por: {c['autor']}")
    else:
        st.info("No hay crónicas publicadas aún")

elif menu == "⚠️ Denuncias":
    st.title("⚠️ Denuncias Ciudadanas")
    st.markdown("*Todas las denuncias son anónimas y serán investigadas*")
    
    tab_den, tab_ver = st.tabs(["📝 Hacer Denuncia", "📋 Ver Denuncias"])
    
    with tab_den:
        with st.form("form_denuncia"):
            nombre = st.text_input("Tu nombre (puede ser anónimo)")
            titulo_den = st.text_input("Título de la denuncia")
            desc = st.text_area("Descripción detallada", height=150)
            ubicacion = st.text_input("Ubicación del hecho")
            if st.form_submit_button("🚨 Enviar Denuncia"):
                if titulo_den and desc:
                    if guardar_denuncia(nombre, titulo_den, desc, ubicacion):
                        st.success("✅ Denuncia enviada. Las autoridades la revisarán.")
                        st.balloons()
                    else:
                        st.error("❌ Error al enviar")
                else:
                    st.warning("⚠️ Título y descripción son obligatorios")
    
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
    
    tab_op, tab_ver = st.tabs(["💭 Dar Opinión", "📖 Ver Opiniones"])
    
    with tab_op:
        with st.form("form_opinion"):
            usuario = st.text_input("Tu nombre")
            comentario = st.text_area("Tu opinión", height=100)
            calificacion = st.slider("Calificación", 1, 5, 5)
            if st.form_submit_button("Enviar Opinión"):
                if usuario and comentario:
                    guardar_opinion(usuario, comentario, calificacion)
                    st.success("✅ Gracias por tu opinión!")
                    st.balloons()
                else:
                    st.warning("⚠️ Nombre y comentario son obligatorios")
    
    with tab_ver:
        opiniones = obtener_opiniones()
        if not opiniones.empty:
            for _, op in opiniones.iterrows():
                estrellas = "⭐" * op['calificacion'] + "☆" * (5 - op['calificacion'])
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <strong>{op['usuario']}</strong> {estrellas}<br>
                    "{op['comentario']}"<br>
                    <small>📅 {op['fecha']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay opiniones aún. ¡Sé el primero en opinar!")

# --- FOOTER ---
st.markdown("""
<div class="bronze-footer">
    <div style="position: absolute; top: 15px; left: 15px; width: 15px; height: 15px; background: radial-gradient(circle, #999, #333); border-radius: 50%;"></div>
    <div style="position: absolute; top: 15px; right: 15px; width: 15px; height: 15px; background: radial-gradient(circle, #999, #333); border-radius: 50%;"></div>
    <div style="position: absolute; bottom: 15px; left: 15px; width: 15px; height: 15px; background: radial-gradient(circle, #999, #333); border-radius: 50%;"></div>
    <div style="position: absolute; bottom: 15px; right: 15px; width: 15px; height: 15px; background: radial-gradient(circle, #999, #333); border-radius: 50%;"></div>
    <p style="font-size: 1.3em;">⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproducción total o parcial</p>
    <p style="font-size: 1.1em; letter-spacing: 3px;">DERECHOS RESERVADOS</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
