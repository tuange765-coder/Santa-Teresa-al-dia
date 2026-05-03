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

# --- NOTICIAS DIARIAS AUTOMATICAS (COLOCADA DESPUES DE obtener_noticias) ---
def cargar_noticias_diarias():
    """Carga noticias predeterminadas si no hay noticias en la base de datos"""
    try:
        noticias_existentes = obtener_noticias()
        if noticias_existentes.empty:
            noticias_default = [
                {
                    "titulo": "Buenos dias Santa Teresa",
                    "categoria": "Nacional",
                    "contenido": "Hoy amanece con un clima cálido en nuestra ciudad. La temperatura rondará los 28°C. Aprovecha el dia!",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "Reporte de Vialidad",
                    "categoria": "Nacional",
                    "contenido": "Se reporta tránsito fluido en la Autopista Regional del Centro. Se recomienda precaución en el sector de La Yaguara.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "Deportes",
                    "categoria": "Deportes",
                    "contenido": "La selección venezolana se prepara para su próximo encuentro. Los jugadores entrenan a full.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "Internacional",
                    "categoria": "Internacional",
                    "contenido": "Noticias importantes desde el mundo. Mantente informado con Santa Teresa al Dia.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                },
                {
                    "titulo": "Reportaje del Dia",
                    "categoria": "Reportajes",
                    "contenido": "Conoce la historia de los emprendedores de Santa Teresa que están transformando nuestra comunidad.",
                    "fecha": datetime.now().strftime("%d/%m/%Y")
                }
            ]
            
            with conn.session as s:
                for n in noticias_default:
                    s.execute(text("""
                        INSERT INTO noticias (titulo, categoria, contenido, fecha_publicacion, autor)
                        VALUES (:t, :c, :cont, :f, 'Santa Teresa al Dia')
                    """), {"t": n["titulo"], "c": n["categoria"], "cont": n["contenido"], "f": n["fecha"]})
                s.commit()
            st.info("Noticias diarias cargadas automaticamente")
    except Exception as e:
        pass

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

# --- CARGAR NOTICIAS DIARIAS AL INICIAR (AHORA SÍ DESPUÉS DE LA DEFINICIÓN) ---
cargar_noticias_diarias()

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

# --- ENCABEZADO ---
st.markdown("""
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
        "Portada", "Noticias", "Reflexiones", "Multimedia",
        "Guia Comercial", "Ventana del Pasado", "Cronicas Reales",
        "Denuncias", "Opiniones"
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
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Panel de Control")
        admin_accion = st.selectbox("Accion", [
            "Publicar Noticia", "Nueva Reflexion", "Agregar a Ventana",
            "Nueva Cronica", "Gestionar Denuncias", "Configurar App"
        ])
    
    if admin_accion == "Publicar Noticia":
        with st.expander("Publicar Noticia", expanded=True):
            titulo = st.text_input("Titulo")
            categoria = st.selectbox("Categoria", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=150)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.button("Publicar"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido, imagen):
                        st.success("Noticia publicada!")
                        st.rerun()
    
    elif admin_accion == "Nueva Reflexion":
        with st.expander("Reflexion", expanded=True):
            titulo = st.text_input("Titulo")
            contenido = st.text_area("Contenido", height=150)
            if st.button("Guardar"):
                if titulo and contenido:
                    guardar_reflexion(titulo, contenido)
                    st.success("Reflexion guardada!")
                    st.rerun()
    
    elif admin_accion == "Agregar a Ventana":
        with st.expander("Registro Historico", expanded=True):
            titulo = st.text_input("Titulo")
            fecha = st.text_input("Fecha")
            contenido = st.text_area("Descripcion", height=150)
            if st.button("Guardar"):
                if titulo and contenido:
                    guardar_ventana(titulo, contenido, fecha)
                    st.success("Registro guardado!")
                    st.rerun()
    
    elif admin_accion == "Nueva Cronica":
        with st.expander("Nueva Cronica", expanded=True):
            titulo = st.text_input("Titulo")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Cronica", height=150)
            if st.button("Guardar"):
                if titulo and contenido:
                    guardar_cronica(titulo, contenido, lugar)
                    st.success("Cronica guardada!")
                    st.rerun()
    
    elif admin_accion == "Gestionar Denuncias":
        st.write("Gestion de Denuncias")
        denuncias = obtener_denuncias()
        for _, d in denuncias.iterrows():
            with st.expander(f"{d['titulo']}"):
                st.write(d['descripcion'])
                nuevo = st.selectbox("Estado", ["Pendiente", "En revision", "Resuelta"], key=f"est_{d['id']}")
                if st.button("Actualizar", key=f"upd_{d['id']}"):
                    actualizar_estatus_denuncia(d['id'], nuevo)
                    st.rerun()
    
    elif admin_accion == "Configurar App":
        precio_actual = obtener_precio_dolar()
        nuevo = st.number_input("Dolar BCV", value=precio_actual)
        if st.button("Actualizar"):
            actualizar_precio_dolar(nuevo)
            st.success("Actualizado!")

# --- PANEL SUPERIOR ---
ahora = datetime.now()
dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

visitas = obtener_visitas()
precio_dolar = obtener_precio_dolar()
efemeride = obtener_efemerides()

st.markdown(f"""
<div class="stats-panel">
    <span style="color: #FFD700;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color: white; font-size: 1.5em;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 Visitas: {visitas:,} | 💵 Dolar: {precio_dolar:.2f} Bs</span>
</div>
""", unsafe_allow_html=True)

# --- CONTENIDO PRINCIPAL ---
if menu == "Portada":
    st.title("Santa Teresa al Dia")
    st.markdown("### Ultimas Noticias")
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.head(4).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:200]}...")
            st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
            st.markdown("---")
    else:
        st.info("No hay noticias disponibles")

elif menu == "Noticias":
    st.title("Noticias")
    cat = st.selectbox("Filtrar", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    noticias = obtener_noticias(cat if cat != "Todas" else None)
    for _, n in noticias.iterrows():
        st.markdown(f"### {n['titulo']}")
        st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
        st.write(n['contenido'])
        if es_admin:
            if st.button("Eliminar", key=f"del_{n['id']}"):
                eliminar_noticia(n['id'])
                st.rerun()
        st.markdown("---")

elif menu == "Reflexiones":
    st.title("Reflexiones")
    ref = obtener_reflexion_activa()
    if ref:
        st.markdown(f"### {ref['titulo']}")
        st.write(ref['contenido'])
        st.caption(f"{ref['autor']} - {ref['fecha']}")

elif menu == "Multimedia":
    st.title("Multimedia")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

elif menu == "Guia Comercial":
    st.title("Guia Comercial")
    st.markdown("[Ir a la Guia Comercial](https://williantuguiasantateresa.streamlit.app)")

elif menu == "Ventana del Pasado":
    st.title("Ventana del Pasado")
    for _, r in obtener_ventana().iterrows():
        st.markdown(f"### {r['titulo']}")
        st.caption(r['fecha_evento'])
        st.write(r['contenido'])

elif menu == "Cronicas Reales":
    st.title("Cronicas Reales")
    for _, c in obtener_cronicas().iterrows():
        with st.expander(c['titulo']):
            st.write(c['contenido'])

elif menu == "Denuncias":
    st.title("Denuncias")
    with st.form("denuncia"):
        nombre = st.text_input("Tu nombre")
        titulo = st.text_input("Titulo")
        desc = st.text_area("Descripcion")
        ubic = st.text_input("Ubicacion")
        if st.form_submit_button("Enviar"):
            guardar_denuncia(nombre, titulo, desc, ubic)
            st.success("Denuncia enviada!")

elif menu == "Opiniones":
    st.title("Opiniones")
    with st.form("opinion"):
        usuario = st.text_input("Nombre")
        comentario = st.text_area("Comentario")
        if st.form_submit_button("Enviar"):
            guardar_opinion(usuario, comentario, 5)
            st.success("Opinion enviada!")

# --- FOOTER ---
st.markdown("""
<div class="bronze-footer">
    <p>⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproduccion total o parcial - Derechos Reservados</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
