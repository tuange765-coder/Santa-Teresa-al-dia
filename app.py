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

# --- CREAR TABLAS SOLO SI NO EXISTEN ---
def crear_tablas():
    try:
        with conn.session as s:
            # Noticias
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                categoria TEXT,
                contenido TEXT,
                imagen TEXT,
                fecha TEXT,
                autor TEXT
            )
            """))
            
            # Negocios
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS negocios (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                categoria TEXT,
                resena TEXT,
                imagen TEXT,
                direccion TEXT,
                telefono TEXT,
                horario TEXT,
                fecha TEXT
            )
            """))
            
            # Reflexiones
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS reflexiones (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                contenido TEXT,
                versiculo TEXT,
                autor TEXT,
                fecha TEXT,
                activo BOOLEAN DEFAULT TRUE
            )
            """))
            
            # Cronicas
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS cronicas (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                contenido TEXT,
                autor TEXT,
                fecha TEXT,
                lugar TEXT
            )
            """))
            
            # Denuncias
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS denuncias (
                id SERIAL PRIMARY KEY,
                denunciante TEXT,
                titulo TEXT,
                descripcion TEXT,
                ubicacion TEXT,
                fecha TEXT,
                estatus TEXT DEFAULT 'Pendiente'
            )
            """))
            
            # Opiniones
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS opiniones (
                id SERIAL PRIMARY KEY,
                usuario TEXT,
                comentario TEXT,
                calificacion INTEGER,
                fecha TEXT,
                aprobada BOOLEAN DEFAULT FALSE
            )
            """))
            
            # Visitas
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 0
            )
            """))
            
            # Configuracion
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                logo TEXT,
                dolar REAL DEFAULT 65.0
            )
            """))
            
            # Insertar datos iniciales
            res = s.execute(text("SELECT COUNT(*) FROM visitas WHERE id = 1")).fetchone()
            if res[0] == 0:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            
            res2 = s.execute(text("SELECT COUNT(*) FROM configuracion WHERE id = 1")).fetchone()
            if res2[0] == 0:
                s.execute(text("INSERT INTO configuracion (id, logo, dolar) VALUES (1, NULL, 65.0)"))
            
            # Insertar cronica inicial
            res3 = s.execute(text("SELECT COUNT(*) FROM cronicas")).fetchone()
            if res3[0] == 0:
                s.execute(text("""
                    INSERT INTO cronicas (titulo, contenido, autor, fecha, lugar)
                    VALUES ('Los Valles del Tuy', 'Los Valles del Tuy fueron testigos de importantes batallas por la independencia. Hoy son una próspera región agrícola e industrial.', 'Cronista', '1781', 'Valles del Tuy')
                """))
            
            # Insertar reflexion inicial
            res4 = s.execute(text("SELECT COUNT(*) FROM reflexiones")).fetchone()
            if res4[0] == 0:
                s.execute(text("""
                    INSERT INTO reflexiones (titulo, contenido, versiculo, autor, fecha, activo)
                    VALUES ('La Paz de Dios', 'No se angustien por nada; presenten sus peticiones delante de Dios.', 'Filipenses 4:6-7', 'Ministerio', '2026-01-01', TRUE)
                """))
            
            # Insertar noticias iniciales
            res5 = s.execute(text("SELECT COUNT(*) FROM noticias")).fetchone()
            if res5[0] == 0:
                noticias_iniciales = [
                    ("Bienvenidos a Santa Teresa al Dia", "Nacional", "Un espacio para mantenernos informados y conectados como comunidad.", "2026-01-01", "Admin"),
                    ("Santa Teresa: Tierra de progreso", "Nacional", "Nuestra ciudad sigue creciendo y desarrollándose cada día.", "2026-01-01", "Admin"),
                    ("Cultura y Tradición", "Reportajes", "Conoce las tradiciones que nos identifican como tuyeros.", "2026-01-01", "Admin")
                ]
                for n in noticias_iniciales:
                    s.execute(text("INSERT INTO noticias (titulo, categoria, contenido, fecha, autor) VALUES (:t, :c, :cont, :f, :a)"),
                             {"t": n[0], "c": n[1], "cont": n[2], "f": n[3], "a": n[4]})
            
            s.commit()
            return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

crear_tablas()

# --- FUNCION DOLAR BCV (SIMPLE) ---
def obtener_dolar():
    try:
        # Intentar API
        response = requests.get("https://ve.dolarapi.com/v1/dolares", timeout=5)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                if item.get("nombre") == "BCV" and "precio" in item:
                    return float(item["precio"])
    except:
        pass
    return 65.0  # Valor por defecto

def actualizar_dolar():
    try:
        precio = obtener_dolar()
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET dolar = :p WHERE id = 1"), {"p": precio})
            s.commit()
    except:
        pass

def get_dolar():
    try:
        res = conn.query("SELECT dolar FROM configuracion WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 65.0
    except:
        return 65.0

# --- FUNCIONES GENERALES ---
def actualizar_visitas():
    try:
        with conn.session as s:
            s.execute(text("UPDATE visitas SET conteo = conteo + 1 WHERE id = 1"))
            s.commit()
    except:
        pass

def get_visitas():
    try:
        res = conn.query("SELECT conteo FROM visitas WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 0
    except:
        return 0

def get_logo():
    try:
        res = conn.query("SELECT logo FROM configuracion WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else None
    except:
        return None

def save_logo(b64):
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET logo = :l WHERE id = 1"), {"l": b64})
            s.commit()
        return True
    except:
        return False

def img_to_base64(file):
    if file:
        try:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        except:
            return None
    return None

def video_to_base64(file):
    if file:
        try:
            return base64.b64encode(file.read()).decode()
        except:
            return None
    return None

def audio_to_base64(file):
    if file:
        try:
            return base64.b64encode(file.read()).decode()
        except:
            return None
    return None

# --- NOTICIAS ---
def add_noticia(titulo, categoria, contenido, imagen):
    try:
        ahora = get_fecha_hora_venezuela()
        img = img_to_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, imagen, fecha, autor)
                VALUES (:t, :c, :cont, :i, :f, 'Admin')
            """), {"t": titulo, "c": categoria, "cont": contenido, "i": img, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def get_noticias():
    try:
        return conn.query("SELECT * FROM noticias ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def delete_noticia(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM noticias WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- NEGOCIOS ---
def add_negocio(nombre, categoria, resena, direccion, telefono, horario, imagen):
    try:
        ahora = get_fecha_hora_venezuela()
        img = img_to_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO negocios (nombre, categoria, resena, imagen, direccion, telefono, horario, fecha)
                VALUES (:n, :c, :r, :i, :d, :t, :h, :f)
            """), {"n": nombre, "c": categoria, "r": resena, "i": img, "d": direccion, "t": telefono, "h": horario, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def get_negocios():
    try:
        return conn.query("SELECT * FROM negocios ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def delete_negocio(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM negocios WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- REFLEXIONES ---
def add_reflexion(titulo, contenido, versiculo):
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

def get_reflexion_activa():
    try:
        df = conn.query("SELECT * FROM reflexiones WHERE activo = TRUE LIMIT 1", ttl=0)
        return df.iloc[0] if not df.empty else None
    except:
        return None

def get_reflexiones():
    try:
        return conn.query("SELECT * FROM reflexiones ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def delete_reflexion(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM reflexiones WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- CRONICAS ---
def add_cronica(titulo, contenido, lugar):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO cronicas (titulo, contenido, autor, fecha, lugar)
                VALUES (:t, :c, 'Admin', :f, :l)
            """), {"t": titulo, "c": contenido, "f": ahora.strftime("%d/%m/%Y"), "l": lugar})
            s.commit()
        return True
    except:
        return False

def get_cronicas():
    try:
        return conn.query("SELECT * FROM cronicas ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def delete_cronica(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM cronicas WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- DENUNCIAS ---
def add_denuncia(denunciante, titulo, descripcion, ubicacion):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO denuncias (denunciante, titulo, descripcion, ubicacion, fecha, estatus)
                VALUES (:d, :t, :desc, :u, :f, 'Pendiente')
            """), {"d": denunciante or "Anonimo", "t": titulo, "desc": descripcion, "u": ubicacion, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def get_denuncias():
    try:
        return conn.query("SELECT * FROM denuncias ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def update_denuncia_status(id_, status):
    try:
        with conn.session as s:
            s.execute(text("UPDATE denuncias SET estatus = :e WHERE id = :id"), {"e": status, "id": id_})
            s.commit()
        return True
    except:
        return False

def delete_denuncia(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM denuncias WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- OPINIONES ---
def add_opinion(usuario, comentario, calificacion):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO opiniones (usuario, comentario, calificacion, fecha, aprobada)
                VALUES (:u, :c, :cal, :f, FALSE)
            """), {"u": usuario, "c": comentario, "cal": calificacion, "f": ahora.strftime("%d/%m/%Y %H:%M")})
            s.commit()
        return True
    except:
        return False

def get_opiniones(aprobadas=True):
    try:
        if aprobadas:
            return conn.query("SELECT * FROM opiniones WHERE aprobada = TRUE ORDER BY id DESC", ttl=0)
        else:
            return conn.query("SELECT * FROM opiniones ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def approve_opinion(id_):
    try:
        with conn.session as s:
            s.execute(text("UPDATE opiniones SET aprobada = TRUE WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

def delete_opinion(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM opiniones WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- ACTUALIZAR DOLAR AL INICIAR ---
actualizar_dolar()

# --- CONTAR VISITA ---
if 'visitado' not in st.session_state:
    actualizar_visitas()
    st.session_state.visitado = True

# --- ESTILOS ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%);
}
.main > div {
    background-color: rgba(0,0,0,0.7);
    border-radius: 15px;
    padding: 20px;
    margin: 10px 0;
}
[data-testid="stSidebar"] {
    background-color: rgba(0,0,0,0.85) !important;
    border-right: 3px solid #FFD700;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
h1, h2, h3, h4 {
    color: #FFD700 !important;
}
p, span, label {
    color: white !important;
}
.stButton > button {
    background: linear-gradient(135deg, #FFD700, #CF142B);
    color: white !important;
    border: none;
    font-weight: bold;
    border-radius: 25px;
}
input, textarea, .stSelectbox {
    background-color: rgba(255,255,255,0.95) !important;
    color: black !important;
    border-radius: 12px;
    border: 2px solid #FFD700 !important;
}
.stats-panel {
    background: rgba(0,0,0,0.6);
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

# --- FECHA Y HORA ---
ahora = get_fecha_hora_venezuela()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- LOGO ---
logo = get_logo()
if logo:
    st.markdown(f'<div style="text-align: center;"><img src="{logo}" style="max-width: 200px;"></div>', unsafe_allow_html=True)

# --- ENCABEZADO ---
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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", width=150)
    st.markdown("---")
    
    menu = st.radio("Menu", [
        "🏠 Portada", "📰 Noticias", "🏪 Donde ir - Donde comprar", "🙏 Reflexiones",
        "📜 Cronicas", "⚠️ Denuncias", "💬 Opiniones"
    ])
    
    st.markdown("---")
    
    es_admin = False
    with st.expander("🔐 Admin", expanded=False):
        clave = st.text_input("Clave:", type="password")
        if clave == "Juan*316*" or clave == "1966":
            es_admin = True
            st.success("✅ Acceso concedido")
        elif clave:
            st.error("❌ Clave incorrecta")

# --- PANEL SUPERIOR ---
visitas = get_visitas()
dolar = get_dolar()

st.markdown(f"""
<div class="stats-panel">
    <span style="color: #FFD700;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color: white; font-size: 1.8em;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 Visitas: {visitas:,} | 💵 Dolar BCV: {dolar:.2f} Bs</span>
</div>
""", unsafe_allow_html=True)

# ============================================
# CONTENIDO PRINCIPAL
# ============================================

if menu == "🏠 Portada":
    st.title("Santa Teresa al Dia")
    
    st.markdown("### 📰 Ultimas Noticias")
    noticias = get_noticias()
    if not noticias.empty:
        for _, n in noticias.head(5).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:300]}...")
            st.caption(f"📅 {n['fecha']} | 🏷️ {n['categoria']}")
            st.markdown("---")
    else:
        st.info("No hay noticias disponibles")
    
    st.markdown("---")
    st.markdown("### 🙏 Reflexion del Dia")
    ref = get_reflexion_activa()
    if ref:
        st.markdown(f"**{ref['titulo']}**")
        st.write(ref['contenido'])
        st.caption(f"📖 {ref['versiculo']}")
    
    st.markdown("---")
    st.markdown("### 🏪 Recomendados")
    negocios = get_negocios()
    if not negocios.empty:
        for _, n in negocios.head(3).iterrows():
            st.markdown(f"**{n['nombre']}** - {n['categoria']}")
            st.caption(f"📍 {n['direccion']}")
    else:
        st.info("Pronto más recomendaciones")

elif menu == "📰 Noticias":
    st.title("📰 Noticias")
    
    cat = st.selectbox("Filtrar", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    noticias = get_noticias()
    
    if not noticias.empty:
        for _, n in noticias.iterrows():
            if cat == "Todas" or n['categoria'] == cat:
                st.markdown(f"### {n['titulo']}")
                st.caption(f"📅 {n['fecha']} | 🏷️ {n['categoria']}")
                st.write(n['contenido'])
                st.markdown("---")
    else:
        st.info("No hay noticias")

elif menu == "🏪 Donde ir - Donde comprar":
    st.title("🏪 Donde ir - Donde comprar")
    
    negocios = get_negocios()
    if not negocios.empty:
        for _, n in negocios.iterrows():
            col1, col2 = st.columns([1, 2])
            with col1:
                if n['imagen']:
                    st.image(n['imagen'], use_container_width=True)
                else:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
            with col2:
                st.markdown(f"### 🏪 {n['nombre']}")
                st.caption(f"📌 {n['categoria']}")
                st.write(f"**Reseña:** {n['resena']}")
                if n['direccion']:
                    st.write(f"📍 {n['direccion']}")
                if n['telefono']:
                    st.write(f"📞 {n['telefono']}")
                if n['horario']:
                    st.write(f"⏰ {n['horario']}")
            st.markdown("---")
    else:
        st.info("No hay negocios agregados aún")

elif menu == "🙏 Reflexiones":
    st.title("🙏 Reflexiones")
    
    ref = get_reflexion_activa()
    if ref:
        st.markdown(f"### ✨ {ref['titulo']} ✨")
        st.write(ref['contenido'])
        st.caption(f"📖 {ref['versiculo']} — {ref['autor']}")
    else:
        st.info("No hay reflexión activa")

elif menu == "📜 Cronicas":
    st.title("📜 Cronicas de Santa Teresa")
    
    cronicas = get_cronicas()
    if not cronicas.empty:
        for _, c in cronicas.iterrows():
            with st.expander(f"📖 {c['titulo']} - {c['lugar']}"):
                st.write(c['contenido'])
                st.caption(f"Publicado: {c['fecha']}")
    else:
        st.info("No hay cronicas publicadas")

elif menu == "⚠️ Denuncias":
    st.title("⚠️ Denuncias Ciudadanas")
    
    tab1, tab2 = st.tabs(["📝 Hacer Denuncia", "📋 Ver Denuncias"])
    
    with tab1:
        with st.form("form_denuncia"):
            nombre = st.text_input("Tu nombre (opcional)")
            titulo = st.text_input("Titulo")
            desc = st.text_area("Descripcion", height=150)
            ubic = st.text_input("Ubicacion")
            if st.form_submit_button("Enviar Denuncia"):
                if titulo and desc:
                    add_denuncia(nombre, titulo, desc, ubic)
                    st.success("✅ Denuncia enviada!")
                    st.balloons()
                else:
                    st.warning("⚠️ Titulo y descripcion son obligatorios")
    
    with tab2:
        denuncias = get_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                status_color = "#FFD700" if d['estatus'] == "Pendiente" else "#00FF00"
                st.markdown(f"""
                <div style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <strong>📌 {d['titulo']}</strong><br>
                    <span style="color: {status_color};">Estado: {d['estatus']}</span><br>
                    <small>📍 {d['ubicacion']} | 📅 {d['fecha']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay denuncias registradas")

elif menu == "💬 Opiniones":
    st.title("💬 Opiniones")
    
    tab1, tab2 = st.tabs(["💭 Dar Opinion", "📖 Ver Opiniones"])
    
    with tab1:
        with st.form("form_opinion"):
            usuario = st.text_input("Tu nombre")
            comentario = st.text_area("Tu opinion", height=100)
            estrellas = st.slider("Calificacion", 1, 5, 5)
            if st.form_submit_button("Enviar Opinion"):
                if usuario and comentario:
                    add_opinion(usuario, comentario, estrellas)
                    st.success("✅ Opinion enviada!")
                    st.balloons()
                else:
                    st.warning("⚠️ Nombre y comentario son obligatorios")
    
    with tab2:
        opiniones = get_opiniones(aprobadas=True)
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
            st.info("No hay opiniones aun")

# ============================================
# PANEL DE ADMINISTRACION
# ============================================
if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠️ Admin")
    
    admin_section = st.sidebar.selectbox("Gestionar", [
        "Noticias", "Negocios", "Reflexiones", "Cronicas", "Denuncias", "Opiniones", "Configuracion"
    ])
    
    # ADMIN: NOTICIAS
    if admin_section == "Noticias":
        st.title("📝 Gestionar Noticias")
        
        with st.form("form_noticia"):
            st.subheader("➕ Publicar Nueva Noticia")
            titulo = st.text_input("Titulo")
            categoria = st.selectbox("Categoria", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=200)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            
            if st.form_submit_button("Publicar Noticia"):
                if titulo and contenido:
                    if add_noticia(titulo, categoria, contenido, imagen):
                        st.success("✅ Noticia publicada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Titulo y contenido son obligatorios")
        
        st.markdown("---")
        st.subheader("📋 Noticias Existentes")
        noticias = get_noticias()
        if not noticias.empty:
            for _, n in noticias.iterrows():
                with st.expander(f"{n['titulo']} - {n['fecha']}"):
                    st.write(n['contenido'])
                    if st.button("🗑️ Eliminar", key=f"del_not_{n['id']}"):
                        delete_noticia(n['id'])
                        st.rerun()
        else:
            st.info("No hay noticias")
    
    # ADMIN: NEGOCIOS
    elif admin_section == "Negocios":
        st.title("🏪 Gestionar Negocios")
        
        with st.form("form_negocio"):
            st.subheader("➕ Agregar Negocio")
            nombre = st.text_input("Nombre")
            categoria = st.text_input("Categoria")
            resena = st.text_area("Reseña", height=100)
            direccion = st.text_input("Direccion")
            telefono = st.text_input("Telefono")
            horario = st.text_input("Horario")
            imagen = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
            
            if st.form_submit_button("Agregar Negocio"):
                if nombre and resena:
                    if add_negocio(nombre, categoria, resena, direccion, telefono, horario, imagen):
                        st.success("✅ Negocio agregado!")
                        st.rerun()
                else:
                    st.warning("⚠️ Nombre y reseña son obligatorios")
        
        st.markdown("---")
        st.subheader("📋 Negocios Existentes")
        negocios = get_negocios()
        if not negocios.empty:
            for _, n in negocios.iterrows():
                with st.expander(f"{n['nombre']} - {n['categoria']}"):
                    if n['imagen']:
                        st.image(n['imagen'], width=200)
                    st.write(f"**Reseña:** {n['resena']}")
                    if st.button("🗑️ Eliminar", key=f"del_neg_{n['id']}"):
                        delete_negocio(n['id'])
                        st.rerun()
        else:
            st.info("No hay negocios")
    
    # ADMIN: REFLEXIONES
    elif admin_section == "Reflexiones":
        st.title("🙏 Gestionar Reflexiones")
        
        with st.form("form_reflexion"):
            st.subheader("➕ Nueva Reflexion")
            titulo = st.text_input("Titulo")
            versiculo = st.text_input("Versiculo Biblico")
            contenido = st.text_area("Contenido", height=150)
            
            if st.form_submit_button("Guardar Reflexion"):
                if titulo and contenido:
                    if add_reflexion(titulo, contenido, versiculo):
                        st.success("✅ Reflexion guardada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Titulo y contenido son obligatorios")
        
        st.markdown("---")
        st.subheader("📋 Reflexiones Anteriores")
        reflexiones = get_reflexiones()
        if not reflexiones.empty:
            for _, r in reflexiones.iterrows():
                with st.expander(f"{r['titulo']} - {r['fecha']}"):
                    st.write(r['contenido'])
                    st.caption(f"Versiculo: {r['versiculo']}")
                    if st.button("🗑️ Eliminar", key=f"del_ref_{r['id']}"):
                        delete_reflexion(r['id'])
                        st.rerun()
        else:
            st.info("No hay reflexiones")
    
    # ADMIN: CRONICAS
    elif admin_section == "Cronicas":
        st.title("📜 Gestionar Cronicas")
        
        with st.form("form_cronica"):
            st.subheader("➕ Nueva Cronica")
            titulo = st.text_input("Titulo")
            lugar = st.text_input("Lugar")
            contenido = st.text_area("Contenido", height=150)
            
            if st.form_submit_button("Guardar Cronica"):
                if titulo and contenido:
                    if add_cronica(titulo, contenido, lugar):
                        st.success("✅ Cronica guardada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Titulo y contenido son obligatorios")
        
        st.markdown("---")
        st.subheader("📋 Cronicas Existentes")
        cronicas = get_cronicas()
        if not cronicas.empty:
            for _, c in cronicas.iterrows():
                with st.expander(f"{c['titulo']} - {c['lugar']}"):
                    st.write(c['contenido'])
                    if st.button("🗑️ Eliminar", key=f"del_cron_{c['id']}"):
                        delete_cronica(c['id'])
                        st.rerun()
        else:
            st.info("No hay cronicas")
    
    # ADMIN: DENUNCIAS
    elif admin_section == "Denuncias":
        st.title("⚠️ Gestionar Denuncias")
        
        denuncias = get_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                with st.expander(f"{d['titulo']} - {d['estatus']}"):
                    st.write(f"**Denunciante:** {d['denunciante']}")
                    st.write(f"**Descripcion:** {d['descripcion']}")
                    st.write(f"**Ubicacion:** {d['ubicacion']}")
                    
                    nuevo_estado = st.selectbox(
                        "Cambiar estado",
                        ["Pendiente", "En revision", "Resuelta", "Descartada"],
                        key=f"est_{d['id']}"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Actualizar", key=f"upd_{d['id']}"):
                            update_denuncia_status(d['id'], nuevo_estado)
                            st.rerun()
                    with col2:
                        if st.button("Eliminar", key=f"del_den_{d['id']}"):
                            delete_denuncia(d['id'])
                            st.rerun()
        else:
            st.info("No hay denuncias")
    
    # ADMIN: OPINIONES
    elif admin_section == "Opiniones":
        st.title("💬 Gestionar Opiniones")
        
        st.subheader("⏳ Pendientes de Aprobacion")
        opiniones_pendientes = get_opiniones(aprobadas=False)
        if not opiniones_pendientes.empty:
            for _, op in opiniones_pendientes.iterrows():
                if not op['aprobada']:
                    with st.expander(f"{op['usuario']} - {op['fecha']}"):
                        st.write(op['comentario'])
                        st.write(f"⭐ Calificacion: {op['calificacion']}")
                        
                        if st.button("✅ Aprobar", key=f"aprob_{op['id']}"):
                            approve_opinion(op['id'])
                            st.rerun()
                        if st.button("🗑️ Eliminar", key=f"del_op_{op['id']}"):
                            delete_opinion(op['id'])
                            st.rerun()
        else:
            st.info("No hay opiniones pendientes")
        
        st.markdown("---")
        st.subheader("✅ Opiniones Aprobadas")
        opiniones_aprobadas = get_opiniones(aprobadas=True)
        if not opiniones_aprobadas.empty:
            for _, op in opiniones_aprobadas.iterrows():
                with st.expander(f"{op['usuario']} - {op['fecha']}"):
                    st.write(op['comentario'])
                    if st.button("🗑️ Eliminar", key=f"del_aprob_{op['id']}"):
                        delete_opinion(op['id'])
                        st.rerun()
        else:
            st.info("No hay opiniones aprobadas")
    
    # ADMIN: CONFIGURACION
    elif admin_section == "Configuracion":
        st.title("⚙️ Configuracion")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Logo")
            if logo:
                st.image(logo, width=150)
            nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg"])
            if nuevo_logo and st.button("Guardar Logo"):
                b64 = img_to_base64(nuevo_logo)
                if save_logo(b64):
                    st.success("Logo guardado!")
                    st.rerun()
        
        with col2:
            st.subheader("Dolar BCV")
            st.write(f"Precio actual: {dolar:.2f} Bs/USD")
            if st.button("Actualizar Dolar"):
                nuevo_dolar = obtener_dolar()
                with conn.session as s:
                    s.execute(text("UPDATE configuracion SET dolar = :p WHERE id = 1"), {"p": nuevo_dolar})
                    s.commit()
                st.success(f"Dolar actualizado a {nuevo_dolar:.2f} Bs")
                st.rerun()

# --- FOOTER ---
st.markdown("""
<div class="bronze-footer">
    <p>⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproduccion total o parcial - Derechos Reservados</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
