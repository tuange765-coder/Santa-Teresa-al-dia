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
        (1,1): "Año Nuevo",
        (19,4): "Declaracion de la Independencia",
        (24,6): "Batalla de Carabobo",
        (5,7): "Dia de la Independencia",
        (24,7): "Natalicio de Simon Bolivar",
        (12,10): "Dia de la Resistencia Indigena",
        (25,12): "Navidad"
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

# --- ESTILOS CSS ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%);
}
.main > div {
    background-color: rgba(0, 0, 0, 0.7);
    border-radius: 15px;
    padding: 20px;
}
h1, h2, h3, p, span, label {
    color: white !important;
}
[data-testid="stSidebar"] {
    background-color: rgba(0, 0, 0, 0.85) !important;
    border-right: 3px solid #FFD700;
}
.stButton > button {
    background: linear-gradient(135deg, #FFD700, #CF142B);
    color: white !important;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --- CONTADOR DE VISITAS ---
if 'visitado' not in st.session_state:
    actualizar_contador()
    st.session_state.visitado = True

# --- LOGO ---
logo = obtener_logo()
if logo:
    st.markdown(f'<div style="text-align: center;"><img src="{logo}" style="max-width: 200px;"></div>', unsafe_allow_html=True)

# --- ENCABEZADO ---
st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #FFD700, #00247D, #CF142B); border-radius: 20px; margin-bottom: 20px;">
    <h1>🌟 Santa Teresa al Día 🌟</h1>
    <p>Información, Cultura y Fe para Nuestra Comunidad</p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
    st.title("Menú Principal")
    
    menu = st.radio("Navegar", [
        "Portada", "Noticias", "Reflexiones", "Multimedia",
        "Guía Comercial", "Ventana del Pasado", "Crónicas Reales",
        "Denuncias", "Opiniones"
    ])
    
    st.markdown("---")
    
    # Login Admin
    es_admin = False
    if st.checkbox("🔐 Administrador"):
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
        admin_accion = st.selectbox("Acción", [
            "Publicar Noticia", "Nueva Reflexión", "Agregar a Ventana del Pasado",
            "Nueva Crónica", "Gestionar Denuncias", "Configurar App"
        ])
    
    if admin_accion == "Publicar Noticia":
        with st.expander("📝 Publicar Noticia", expanded=True):
            titulo = st.text_input("Título")
            categoria = st.selectbox("Categoría", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=150)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.button("Publicar"):
                if titulo and contenido:
                    if publicar_noticia(titulo, categoria, contenido, imagen):
                        st.success("Noticia publicada!")
                        st.rerun()
    
    elif admin_accion == "Nueva Reflexión":
        with st.expander("🙏 Nueva Reflexión", expanded=True):
            titulo = st.text_input("Título")
            contenido = st.text_area("Contenido", height=150)
            if st.button("Guardar"):
                if titulo and contenido:
                    if guardar_reflexion(titulo, contenido):
                        st.success("Reflexión guardada!")
                        st.rerun()
    
    elif admin_accion == "Agregar a Ventana del Pasado":
        with st.expander("📜 Agregar Registro", expanded=True):
            titulo = st.text_input("Título")
            fecha = st.text_input("Fecha", placeholder="Ej: 15 de septiembre de 1781")
            contenido = st.text_area("Descripción", height=150)
            if st.button("Guardar"):
                if titulo and contenido:
                    if guardar_ventana(titulo, contenido, fecha):
                        st.success("Registro guardado!")
                        st.rerun()
    
    elif admin_accion == "Nueva Crónica":
        with st.expander("✍️ Nueva Crónica", expanded=True):
            titulo = st.text_input("Título")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Crónica", height=150)
            if st.button("Guardar"):
                if titulo and contenido:
                    if guardar_cronica(titulo, contenido, lugar):
                        st.success("Crónica guardada!")
                        st.rerun()
    
    elif admin_accion == "Gestionar Denuncias":
        st.write("### Gestión de Denuncias")
        denuncias = obtener_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                with st.expander(f"{d['titulo']} - {d['estatus']}"):
                    st.write(f"**Denunciante:** {d['denunciante']}")
                    st.write(f"**Descripción:** {d['descripcion']}")
                    st.write(f"**Ubicación:** {d['ubicacion']}")
                    nuevo_estado = st.selectbox("Estado", ["Pendiente", "En revisión", "Resuelta"], key=f"est_{d['id']}")
                    if st.button("Actualizar", key=f"upd_{d['id']}"):
                        actualizar_estatus_denuncia(d['id'], nuevo_estado)
                        st.rerun()
                    if st.button("Eliminar", key=f"del_{d['id']}"):
                        eliminar_denuncia(d['id'])
                        st.rerun()
    
    elif admin_accion == "Configurar App":
        st.write("### Configuración")
        precio_actual = obtener_precio_dolar()
        nuevo_precio = st.number_input("Precio del Dólar BCV", value=precio_actual, step=0.01)
        if st.button("Actualizar Dólar"):
            actualizar_precio_dolar(nuevo_precio)
            st.success("Actualizado!")
        
        st.markdown("---")
        st.write("### Logo de la App")
        logo_actual = obtener_logo()
        if logo_actual:
            st.image(logo_actual, width=100)
        nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg"])
        if nuevo_logo and st.button("Guardar Logo"):
            logo_b64 = imagen_a_base64(nuevo_logo)
            if guardar_logo(logo_b64):
                st.success("Logo guardado!")
                st.rerun()

# --- PANEL SUPERIOR ---
ahora = datetime.now()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

visitas = obtener_visitas()
precio_dolar = obtener_precio_dolar()
efemeride = obtener_efemerides()

st.markdown(f"""
<div style="background: #1f2937; padding: 15px; border-radius: 15px; border: 2px solid #FFD700; text-align: center; margin-bottom: 20px;">
    <span style="color: #FFD700;">{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year}</span><br>
    <span style="color: white; font-size: 1.5em;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 Visitas: {visitas:,} | 💵 Dólar: {precio_dolar:.2f} Bs</span>
</div>

<div style="background: linear-gradient(135deg, #1a3a5c, #0a1a3a); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
    <span style="color: #FFD700;">📅 EFEMÉRIDES</span><br>
    <span style="color: white;">{efemeride}</span>
</div>
""", unsafe_allow_html=True)

# --- CONTENIDO PRINCIPAL ---
if menu == "Portada":
    st.title("🏠 Portada")
    st.write(f"### Bienvenidos a Santa Teresa al Día")
    st.write("Tu fuente de información, cultura y fe para nuestra comunidad")
    
    st.markdown("---")
    st.markdown("### 📰 Últimas Noticias")
    noticias = obtener_noticias()
    if not noticias.empty:
        for _, n in noticias.head(3).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:200]}...")
            st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
            st.markdown("---")
    else:
        st.info("No hay noticias aún")

elif menu == "Noticias":
    st.title("📰 Noticias")
    categoria = st.selectbox("Filtrar", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    noticias = obtener_noticias(categoria if categoria != "Todas" else None)
    
    if not noticias.empty:
        for _, n in noticias.iterrows():
            st.markdown(f"### {n['titulo']}")
            st.caption(f"{n['fecha_publicacion']} | {n['categoria']}")
            st.write(n['contenido'])
            if es_admin:
                if st.button("🗑️ Eliminar", key=f"del_{n['id']}"):
                    eliminar_noticia(n['id'])
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No hay noticias")

elif menu == "Reflexiones":
    st.title("🙏 Pan de Vida y Reflexiones")
    reflexion = obtener_reflexion_activa()
    if reflexion is not None:
        st.markdown(f"""
        <div style="background: rgba(0,0,0,0.5); padding: 30px; border-radius: 15px; text-align: center;">
            <h2 style="color: #FFD700;">✨ {reflexion['titulo']} ✨</h2>
            <p style="font-size: 1.2em;">{reflexion['contenido']}</p>
            <p><i>— {reflexion['autor']}, {reflexion['fecha']}</i></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No hay reflexión activa")

elif menu == "Multimedia":
    st.title("🎬 Multimedia")
    tab1, tab2, tab3 = st.tabs(["Videos", "Música", "Radio"])
    with tab1:
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    with tab2:
        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
    with tab3:
        st.audio("https://streaming.listen2myradio.com/example")

elif menu == "Guía Comercial":
    st.title("🏪 Guía Comercial")
    st.markdown("""
    <div style="text-align: center; padding: 40px;">
        <a href="https://williantuguiasantateresa.streamlit.app" target="_blank">
            <button style="background: linear-gradient(135deg, #FFD700, #CF142B); padding: 15px 30px; border-radius: 10px; color: white; font-size: 1.2em; border: none;">
                Ir a la Guía Comercial
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

elif menu == "Ventana del Pasado":
    st.title("📜 Ventana del Pasado")
    registros = obtener_ventana()
    if not registros.empty:
        for _, r in registros.iterrows():
            st.markdown(f"### {r['titulo']}")
            st.caption(f"{r['fecha_evento']}")
            st.write(r['contenido'])
            st.markdown("---")
    else:
        st.info("Próximamente más contenido")

elif menu == "Crónicas Reales":
    st.title("✍️ Crónicas Reales")
    cronicas = obtener_cronicas()
    if not cronicas.empty:
        for _, c in cronicas.iterrows():
            with st.expander(f"{c['titulo']} - {c['lugar']}"):
                st.write(c['contenido'])
                st.caption(f"{c['fecha']}")
    else:
        st.info("No hay crónicas")

elif menu == "Denuncias":
    st.title("⚠️ Denuncias Ciudadanas")
    tab1, tab2 = st.tabs(["Hacer Denuncia", "Ver Denuncias"])
    
    with tab1:
        with st.form("form_denuncia"):
            nombre = st.text_input("Tu nombre (opcional)")
            titulo = st.text_input("Título")
            desc = st.text_area("Descripción", height=100)
            ubicacion = st.text_input("Ubicación")
            if st.form_submit_button("Enviar"):
                if titulo and desc:
                    if guardar_denuncia(nombre, titulo, desc, ubicacion):
                        st.success("Denuncia enviada!")
                        st.balloons()
                else:
                    st.warning("Complete los campos")
    
    with tab2:
        denuncias = obtener_denuncias()
        for _, d in denuncias.iterrows():
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <strong>{d['titulo']}</strong><br>
                {d['descripcion'][:100]}...<br>
                <small>Estado: {d['estatus']} | {d['ubicacion']}</small>
            </div>
            """, unsafe_allow_html=True)

elif menu == "Opiniones":
    st.title("💬 Opiniones")
    tab1, tab2 = st.tabs(["Dar Opinión", "Ver Opiniones"])
    
    with tab1:
        with st.form("form_opinion"):
            usuario = st.text_input("Tu nombre")
            comentario = st.text_area("Comentario")
            calificacion = st.slider("Calificación", 1, 5, 5)
            if st.form_submit_button("Enviar"):
                if usuario and comentario:
                    guardar_opinion(usuario, comentario, calificacion)
                    st.success("Opinión enviada!")
                    st.balloons()
    
    with tab2:
        opiniones = obtener_opiniones()
        for _, op in opiniones.iterrows():
            estrellas = "⭐" * op['calificacion']
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <strong>{op['usuario']}</strong> {estrellas}<br>
                "{op['comentario']}"<br>
                <small>{op['fecha']}</small>
            </div>
            """, unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; padding: 30px; margin-top: 50px; background: linear-gradient(145deg, #8c6a31, #5d431a); border-radius: 15px;">
    <p style="color: #ffd700;">⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p style="color: #ffd700;">Prohibida la reproducción total o parcial - Derechos Reservados</p>
    <p style="color: #ffd700;">Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
