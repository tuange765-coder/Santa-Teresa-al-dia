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

# ============================================
# CONFIGURACION DE PAGINA
# ============================================
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide"
)

# ============================================
# ZONA HORARIA DE VENEZUELA
# ============================================
CARACAS_TZ = pytz.timezone('America/Caracas')

def get_fecha_hora_venezuela():
    ahora_utc = datetime.now(pytz.UTC)
    ahora_caracas = ahora_utc.astimezone(CARACAS_TZ)
    return ahora_caracas

# ============================================
# CONEXION A NEON (BASE DE DATOS)
# ============================================
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

# ============================================
# RECONSTRUIR TABLAS (SOLO UNA VEZ)
# ============================================
def reconstruir_tablas():
    try:
        with conn.session as s:
            # Eliminar tablas existentes
            s.execute(text("DROP TABLE IF EXISTS noticias CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS negocios CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS reflexiones CASCADE"))
            s.execute(text("DROP TABLE IF EXISTS cronicas CASCADE"))
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
                titulo TEXT,
                categoria TEXT,
                contenido TEXT,
                imagen_url TEXT,
                fecha TEXT,
                autor TEXT
            )
            """))
            
            # Tabla de negocios
            s.execute(text("""
            CREATE TABLE negocios (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                categoria TEXT,
                resena TEXT,
                imagen_url TEXT,
                direccion TEXT,
                telefono TEXT,
                horario TEXT,
                fecha TEXT
            )
            """))
            
            # Tabla de reflexiones
            s.execute(text("""
            CREATE TABLE reflexiones (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                contenido TEXT,
                versiculo TEXT,
                autor TEXT,
                fecha TEXT,
                activo BOOLEAN DEFAULT TRUE
            )
            """))
            
            # Tabla de cronicas
            s.execute(text("""
            CREATE TABLE cronicas (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                contenido TEXT,
                autor TEXT,
                fecha TEXT,
                lugar TEXT,
                estado TEXT
            )
            """))
            
            # Tabla de videos
            s.execute(text("""
            CREATE TABLE videos (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                video_url TEXT,
                formato TEXT,
                fecha TEXT
            )
            """))
            
            # Tabla de musicas
            s.execute(text("""
            CREATE TABLE musicas (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                audio_url TEXT,
                formato TEXT,
                fecha TEXT
            )
            """))
            
            # Tabla de denuncias
            s.execute(text("""
            CREATE TABLE denuncias (
                id SERIAL PRIMARY KEY,
                denunciante TEXT,
                titulo TEXT,
                descripcion TEXT,
                ubicacion TEXT,
                fecha TEXT,
                estatus TEXT DEFAULT 'Pendiente'
            )
            """))
            
            # Tabla de opiniones
            s.execute(text("""
            CREATE TABLE opiniones (
                id SERIAL PRIMARY KEY,
                usuario TEXT,
                comentario TEXT,
                calificacion INTEGER,
                fecha TEXT,
                aprobada BOOLEAN DEFAULT FALSE
            )
            """))
            
            # Tabla de visitas (inicia en 1500)
            s.execute(text("""
            CREATE TABLE visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 1500
            )
            """))
            
            # Tabla de configuracion
            s.execute(text("""
            CREATE TABLE configuracion (
                id INTEGER PRIMARY KEY,
                logo_url TEXT,
                dolar REAL DEFAULT 489.55
            )
            """))
            
            # Insertar datos iniciales
            s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 1500)"))
            s.execute(text("INSERT INTO configuracion (id, logo_url, dolar) VALUES (1, NULL, 489.55)"))
            
            # Insertar cronicas iniciales de Venezuela
            cronicas_iniciales = [
                ("Los Valles del Tuy", "Los Valles del Tuy fueron testigos de importantes batallas por la independencia. Hoy son una próspera región agrícola e industrial.", "Cronista", "1781", "Valles del Tuy", "Miranda"),
                ("La Batalla de Carabobo", "El 24 de junio de 1821, el Ejército Patriota liderado por Simón Bolívar derrotó a las fuerzas realistas, sellando la independencia de Venezuela.", "Cronista", "1821", "Campo de Carabobo", "Carabobo"),
                ("Nacimiento del Libertador", "Simón José Antonio de la Santísima Trinidad Bolívar Palacios Ponte y Blanco nació en Caracas el 24 de julio de 1783.", "Cronista", "1783", "Caracas", "Distrito Capital"),
                ("La Guerra Federal", "Entre 1859 y 1863, Venezuela vivió una cruenta guerra civil que enfrentó a conservadores y liberales.", "Cronista", "1859", "Todo el territorio nacional", "Varios estados")
            ]
            for c in cronicas_iniciales:
                s.execute(text("INSERT INTO cronicas (titulo, contenido, autor, fecha, lugar, estado) VALUES (:t, :c, :a, :f, :l, :e)"),
                         {"t": c[0], "c": c[1], "a": c[2], "f": c[3], "l": c[4], "e": c[5]})
            
            # Insertar reflexion inicial (Reina Valera 1960)
            s.execute(text("""
                INSERT INTO reflexiones (titulo, contenido, versiculo, autor, fecha, activo)
                VALUES ('La Paz de Dios', 
                'Querido hermano, no te angusties por nada. En lugar de eso, presenta tus peticiones delante de Dios. Él te dará una paz que no puedes explicar, pero que cuidará tu corazón y tus pensamientos.', 
                'Filipenses 4:6-7 (Reina Valera 1960)', 
                'Ministerio Santa Teresa', 
                '2026-01-01', 
                TRUE)
            """))
            
            # Insertar noticias iniciales
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            noticias_iniciales = [
                ("Bienvenidos a Santa Teresa al Dia", "Nacional", "Un espacio para mantenernos informados y conectados como comunidad.", fecha_actual, "Admin"),
                ("Santa Teresa: Tierra de progreso", "Nacional", "Nuestra ciudad sigue creciendo y desarrollándose cada día.", fecha_actual, "Admin"),
                ("Selección Venezolana se prepara", "Deportes", "La Vinotinto continúa su preparación para los próximos compromisos internacionales.", fecha_actual, "Admin"),
                ("Situación internacional", "Internacional", "Análisis de los principales sucesos que afectan la economía global.", fecha_actual, "Admin")
            ]
            for n in noticias_iniciales:
                s.execute(text("INSERT INTO noticias (titulo, categoria, contenido, fecha, autor) VALUES (:t, :c, :cont, :f, :a)"),
                         {"t": n[0], "c": n[1], "cont": n[2], "f": n[3], "a": n[4]})
            
            s.commit()
            st.success("✅ Tablas reconstruidas correctamente")
            return True
    except Exception as e:
        st.error(f"Error al reconstruir tablas: {e}")
        return False

# Ejecutar reconstruccion (solo se ejecutará una vez)
if 'tablas_reconstruidas' not in st.session_state:
    reconstruir_tablas()
    st.session_state.tablas_reconstruidas = True

# ============================================
# FUNCION DOLAR BCV
# ============================================
def get_dolar():
    try:
        res = conn.query("SELECT dolar FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty:
            return float(res.iloc[0,0])
        return 489.55
    except:
        return 489.55

def actualizar_dolar_manual(nuevo_valor):
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET dolar = :p WHERE id = 1"), {"p": nuevo_valor})
            s.commit()
        return True
    except:
        return False

dolar = get_dolar()

# ============================================
# FUNCIONES GENERALES
# ============================================
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
        if not res.empty:
            return int(res.iloc[0,0])
        return 1500
    except:
        return 1500

def get_logo():
    try:
        res = conn.query("SELECT logo_url FROM configuracion WHERE id = 1", ttl=0)
        if not res.empty and res.iloc[0,0]:
            return res.iloc[0,0]
        return None
    except:
        return None

def save_logo(url):
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET logo_url = :l WHERE id = 1"), {"l": url})
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

# ============================================
# NOTICIAS
# ============================================
def add_noticia(titulo, categoria, contenido, imagen):
    try:
        ahora = get_fecha_hora_venezuela()
        img_url = img_to_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO noticias (titulo, categoria, contenido, imagen_url, fecha, autor)
                VALUES (:t, :c, :cont, :i, :f, 'Admin')
            """), {"t": titulo, "c": categoria, "cont": contenido, "i": img_url, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def get_noticias(categoria=None):
    try:
        if categoria and categoria != "Todas":
            return conn.query("SELECT * FROM noticias WHERE categoria = :cat ORDER BY id DESC", 
                            params={"cat": categoria}, ttl=0)
        else:
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

# ============================================
# NEGOCIOS
# ============================================
def add_negocio(nombre, categoria, resena, direccion, telefono, horario, imagen):
    try:
        ahora = get_fecha_hora_venezuela()
        img_url = img_to_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("""
                INSERT INTO negocios (nombre, categoria, resena, imagen_url, direccion, telefono, horario, fecha)
                VALUES (:n, :c, :r, :i, :d, :t, :h, :f)
            """), {"n": nombre, "c": categoria, "r": resena, "i": img_url, "d": direccion, "t": telefono, "h": horario, "f": ahora.strftime("%d/%m/%Y")})
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

# ============================================
# REFLEXIONES
# ============================================
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
        if not df.empty:
            return df.iloc[0]
        return None
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

# ============================================
# CRONICAS
# ============================================
def add_cronica(titulo, contenido, lugar, estado):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO cronicas (titulo, contenido, autor, fecha, lugar, estado)
                VALUES (:t, :c, 'Admin', :f, :l, :e)
            """), {"t": titulo, "c": contenido, "f": ahora.strftime("%d/%m/%Y"), "l": lugar, "e": estado})
            s.commit()
        return True
    except:
        return False

def get_cronicas(estado=None):
    try:
        if estado and estado != "Todos":
            return conn.query("SELECT * FROM cronicas WHERE estado = :e ORDER BY id DESC", 
                            params={"e": estado}, ttl=0)
        else:
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

# ============================================
# VIDEOS
# ============================================
def add_video(titulo, url_video):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO videos (titulo, video_url, formato, fecha)
                VALUES (:t, :u, 'mp4', :f)
            """), {"t": titulo, "u": url_video, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def get_videos():
    try:
        return conn.query("SELECT * FROM videos ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def delete_video(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM videos WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# ============================================
# MUSICA
# ============================================
def add_musica(titulo, url_audio):
    try:
        ahora = get_fecha_hora_venezuela()
        with conn.session as s:
            s.execute(text("""
                INSERT INTO musicas (titulo, audio_url, formato, fecha)
                VALUES (:t, :u, 'mp3', :f)
            """), {"t": titulo, "u": url_audio, "f": ahora.strftime("%d/%m/%Y")})
            s.commit()
        return True
    except:
        return False

def get_musicas():
    try:
        return conn.query("SELECT * FROM musicas ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

def delete_musica(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM musicas WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# ============================================
# DENUNCIAS
# ============================================
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

# ============================================
# OPINIONES
# ============================================
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

# ============================================
# CONTADOR DE VISITAS
# ============================================
if 'visitante_contado' not in st.session_state:
    actualizar_visitas()
    st.session_state.visitante_contado = True

visitas = get_visitas()

# ============================================
# ESTILOS
# ============================================
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
    padding: 35px 25px;
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
.bronze-footer .titulo {
    font-size: 1.8em;
    letter-spacing: 4px;
}
.screw {
    position: absolute;
    width: 22px;
    height: 22px;
    background: radial-gradient(circle at 30% 30%, #bbb, #444);
    border-radius: 50%;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.6);
    border: 1px solid #d4af37;
}
.screw::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 15%;
    width: 70%;
    height: 2px;
    background: #333;
    transform: translateY(-50%) rotate(45deg);
}
.screw::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 15%;
    width: 70%;
    height: 2px;
    background: #333;
    transform: translateY(-50%) rotate(-45deg);
}
.screw-tl { top: 15px; left: 15px; }
.screw-tr { top: 15px; right: 15px; }
.screw-bl { bottom: 15px; left: 15px; }
.screw-br { bottom: 15px; right: 15px; }
</style>
""", unsafe_allow_html=True)

# ============================================
# FECHA Y HORA
# ============================================
ahora = get_fecha_hora_venezuela()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# ============================================
# LOGO
# ============================================
logo = get_logo()
if logo:
    st.markdown(f'<div style="text-align: center;"><img src="{logo}" style="max-width: 200px;"></div>', unsafe_allow_html=True)

# ============================================
# ENCABEZADO
# ============================================
st.markdown(f"""
<div style="text-align: center; margin-bottom: 20px;">
    <div style="background: linear-gradient(135deg, #FFD700, #00247D, #CF142B); border-radius: 20px; padding: 20px;">
        <h1 style="color: white;">🌟 Santa Teresa al Dia 🌟</h1>
        <p style="color: white;">Informacion, Cultura y Fe para Nuestra Comunidad</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", width=150)
    st.markdown("---")
    
    menu = st.radio("📋 Menu Principal", [
        "🏠 Portada", "📰 Noticias", "🏪 Donde ir - Donde comprar", "🙏 Reflexiones",
        "📜 Cronicas", "🎬 Multimedia", "⚠️ Denuncias", "💬 Opiniones"
    ])
    
    st.markdown("---")
    
    # Panel de Administracion
    es_admin = False
    with st.expander("🔐 Panel de Control", expanded=False):
        clave = st.text_input("Clave de Administrador:", type="password")
        if clave == "Juan*316*" or clave == "1966":
            es_admin = True
            st.success("✅ Acceso concedido")
        elif clave:
            st.error("❌ Clave incorrecta")

# ============================================
# PANEL SUPERIOR
# ============================================
st.markdown(f"""
<div class="stats-panel">
    <span style="color: #FFD700;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color: white; font-size: 1.8em;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color: #FFD700;">👥 Visitantes: {visitas:,} | 💵 Dolar BCV: {dolar:.2f} Bs</span>
</div>
""", unsafe_allow_html=True)

# ============================================
# CONTENIDO PRINCIPAL
# ============================================

# --- PORTADA ---
if menu == "🏠 Portada":
    st.title("🌟 Santa Teresa al Dia")
    
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
    if ref is not None:
        st.markdown(f"**{ref['titulo']}**")
        st.write(ref['contenido'])
        st.caption(f"📖 {ref['versiculo']}")
    
    st.markdown("---")
    st.markdown("### 🏪 Recomendados")
    negocios = get_negocios()
    if not negocios.empty:
        for _, n in negocios.head(3).iterrows():
            st.markdown(f"**{n['nombre']}** - {n['categoria']}")

# --- NOTICIAS ---
elif menu == "📰 Noticias":
    st.title("📰 Noticias")
    
    tab_nac, tab_inter, tab_dep = st.tabs(["🇻🇪 Nacionales", "🌍 Internacionales", "⚽ Deportes"])
    
    with tab_nac:
        noticias = get_noticias(categoria="Nacional")
        if not noticias.empty:
            for _, n in noticias.iterrows():
                st.markdown(f"### {n['titulo']}")
                st.caption(f"📅 {n['fecha']}")
                st.write(n['contenido'])
                st.markdown("---")
        else:
            st.info("No hay noticias Nacionales")
    
    with tab_inter:
        noticias = get_noticias(categoria="Internacional")
        if not noticias.empty:
            for _, n in noticias.iterrows():
                st.markdown(f"### {n['titulo']}")
                st.caption(f"📅 {n['fecha']}")
                st.write(n['contenido'])
                st.markdown("---")
        else:
            st.info("No hay noticias Internacionales")
    
    with tab_dep:
        noticias = get_noticias(categoria="Deportes")
        if not noticias.empty:
            for _, n in noticias.iterrows():
                st.markdown(f"### {n['titulo']}")
                st.caption(f"📅 {n['fecha']}")
                st.write(n['contenido'])
                st.markdown("---")
        else:
            st.info("No hay noticias de Deportes")

# --- DONDE IR - DONDE COMPRAR ---
elif menu == "🏪 Donde ir - Donde comprar":
    st.title("🏪 Donde ir - Donde comprar")
    
    negocios = get_negocios()
    if not negocios.empty:
        for _, n in negocios.iterrows():
            col1, col2 = st.columns([1, 2])
            with col1:
                if n['imagen_url']:
                    st.image(n['imagen_url'], use_container_width=True)
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

# --- REFLEXIONES ---
elif menu == "🙏 Reflexiones":
    st.title("🙏 Pan de Vida y Reflexiones")
    
    ref = get_reflexion_activa()
    if ref is not None:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(0,0,0,0.5), rgba(0,36,125,0.5)); 
                    padding: 30px; border-radius: 20px; border-left: 8px solid #FFD700;">
            <h2 style="color: #FFD700; text-align: center;">✨ {ref['titulo']} ✨</h2>
            <p style="font-size: 1.2em; text-align: center;">{ref['contenido']}</p>
            <p style="margin-top: 15px; text-align: center;"><i>📖 {ref['versiculo']}</i></p>
            <p style="margin-top: 20px; text-align: right;"><i>— {ref['autor']}, {ref['fecha']}</i></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No hay reflexión activa para hoy")

# --- CRONICAS ---
elif menu == "📜 Cronicas":
    st.title("📜 Cronicas de Venezuela")
    
    estados_venezuela = ["Todos", "Miranda", "Carabobo", "Distrito Capital", "Zulia", "Lara", "Aragua", "Bolivar", "Anzoategui", "Merida", "Tachira", "Nueva Esparta", "Sucre", "Falcon", "Barinas", "Portuguesa", "Guarico", "Cojedes", "Trujillo", "Yaracuy", "Apure", "Amazonas", "Delta Amacuro", "Vargas"]
    estado_filtro = st.selectbox("Filtrar por estado", estados_venezuela)
    
    cronicas = get_cronicas(estado_filtro if estado_filtro != "Todos" else None)
    if not cronicas.empty:
        for _, c in cronicas.iterrows():
            with st.expander(f"📖 {c['titulo']} - {c['lugar']}, {c['estado']}"):
                st.write(c['contenido'])
                st.caption(f"Publicado: {c['fecha']}")
    else:
        st.info("No hay cronicas disponibles")

# --- MULTIMEDIA ---
elif menu == "🎬 Multimedia":
    st.title("🎬 Multimedia")
    
    tab_videos, tab_musica, tab_radio = st.tabs(["🎥 Videos", "🎵 Musica", "📻 Radio"])
    
    with tab_videos:
        videos = get_videos()
        if not videos.empty:
            for _, v in videos.iterrows():
                st.markdown(f"**{v['titulo']}**")
                st.video(v['video_url'])
                st.caption(f"Subido: {v['fecha']}")
                st.markdown("---")
        else:
            st.info("No hay videos disponibles")
    
    with tab_musica:
        musicas = get_musicas()
        if not musicas.empty:
            for _, m in musicas.iterrows():
                st.markdown(f"**{m['titulo']}**")
                st.audio(m['audio_url'])
                st.caption(f"Agregado: {m['fecha']}")
                st.markdown("---")
        else:
            st.info("No hay musica disponible")
    
    with tab_radio:
        st.markdown("### 📻 Radio Online")
        st.audio("https://streaming.radiosenlinea.net/9090/stream")

# --- DENUNCIAS ---
elif menu == "⚠️ Denuncias":
    st.title("⚠️ Denuncias Ciudadanas")
    
    tab1, tab2 = st.tabs(["📝 Hacer Denuncia", "📋 Ver Denuncias"])
    
    with tab1:
        with st.form("form_denuncia"):
            nombre = st.text_input("Tu nombre (opcional)")
            titulo = st.text_input("Título de la denuncia")
            desc = st.text_area("Descripción detallada", height=150)
            ubic = st.text_input("Ubicación del hecho")
            if st.form_submit_button("🚨 Enviar Denuncia"):
                if titulo and desc:
                    add_denuncia(nombre, titulo, desc, ubic)
                    st.success("✅ Denuncia enviada")
                    st.balloons()
                else:
                    st.warning("⚠️ Título y descripción son obligatorios")
    
    with tab2:
        denuncias = get_denuncias()
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
            st.info("No hay denuncias registradas")

# --- OPINIONES ---
elif menu == "💬 Opiniones":
    st.title("💬 Opiniones")
    
    tab1, tab2 = st.tabs(["💭 Dar Opinion", "📖 Ver Opiniones"])
    
    with tab1:
        with st.form("form_opinion"):
            usuario = st.text_input("Tu nombre")
            comentario = st.text_area("Tu opinión", height=100)
            estrellas = st.slider("Calificación", 1, 5, 5)
            if st.form_submit_button("Enviar Opinión"):
                if usuario and comentario:
                    add_opinion(usuario, comentario, estrellas)
                    st.success("✅ Gracias por tu opinión!")
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
            st.info("No hay opiniones aún")

# ============================================
# PANEL DE ADMINISTRACION
# ============================================
if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠️ Panel de Control")
    
    admin_option = st.sidebar.radio("Seleccionar", [
        "📝 Noticias",
        "🏪 Negocios",
        "🙏 Reflexiones",
        "📜 Cronicas",
        "🎬 Videos",
        "🎵 Musica",
        "⚠️ Denuncias",
        "💬 Opiniones",
        "⚙️ Configuracion"
    ])
    
    # --- ADMIN: NOTICIAS ---
    if admin_option == "📝 Noticias":
        st.title("📝 Gestionar Noticias")
        
        with st.form("form_noticia"):
            st.subheader("➕ Publicar Nueva Noticia")
            titulo = st.text_input("Título")
            categoria = st.selectbox("Categoría", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=200)
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("📢 Publicar"):
                if titulo and contenido:
                    if add_noticia(titulo, categoria, contenido, imagen):
                        st.success("✅ Noticia publicada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Complete los campos")
        
        st.markdown("---")
        st.subheader("📋 Noticias Existentes")
        noticias = get_noticias()
        if not noticias.empty:
            for _, n in noticias.iterrows():
                with st.expander(f"{n['titulo']} - {n['fecha']}"):
                    if n['imagen_url']:
                        st.image(n['imagen_url'], width=200)
                    st.write(n['contenido'])
                    if st.button("🗑️ Eliminar", key=f"del_not_{n['id']}"):
                        delete_noticia(n['id'])
                        st.rerun()
        else:
            st.info("No hay noticias")
    
    # --- ADMIN: NEGOCIOS ---
    elif admin_option == "🏪 Negocios":
        st.title("🏪 Gestionar Negocios")
        
        with st.form("form_negocio"):
            st.subheader("➕ Agregar Negocio")
            nombre = st.text_input("Nombre")
            categoria = st.text_input("Categoría")
            resena = st.text_area("Reseña", height=100)
            direccion = st.text_input("Dirección")
            telefono = st.text_input("Teléfono")
            horario = st.text_input("Horario")
            imagen = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("🏪 Agregar"):
                if nombre and resena:
                    if add_negocio(nombre, categoria, resena, direccion, telefono, horario, imagen):
                        st.success("✅ Negocio agregado!")
                        st.rerun()
                else:
                    st.warning("⚠️ Complete los campos")
        
        st.markdown("---")
        st.subheader("📋 Negocios Existentes")
        negocios = get_negocios()
        if not negocios.empty:
            for _, n in negocios.iterrows():
                with st.expander(f"{n['nombre']} - {n['categoria']}"):
                    if n['imagen_url']:
                        st.image(n['imagen_url'], width=200)
                    st.write(n['resena'])
                    if st.button("🗑️ Eliminar", key=f"del_neg_{n['id']}"):
                        delete_negocio(n['id'])
                        st.rerun()
        else:
            st.info("No hay negocios")
    
    # --- ADMIN: REFLEXIONES ---
    elif admin_option == "🙏 Reflexiones":
        st.title("🙏 Gestionar Reflexiones")
        
        with st.form("form_reflexion"):
            st.subheader("➕ Nueva Reflexión")
            titulo = st.text_input("Título")
            versiculo = st.text_input("Versículo")
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("🙏 Guardar"):
                if titulo and contenido:
                    if add_reflexion(titulo, contenido, versiculo):
                        st.success("✅ Reflexión guardada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Complete los campos")
        
        st.markdown("---")
        st.subheader("📋 Reflexiones Anteriores")
        reflexiones = get_reflexiones()
        if not reflexiones.empty:
            for _, r in reflexiones.iterrows():
                with st.expander(f"{r['titulo']} - {r['fecha']}"):
                    st.write(r['contenido'])
                    st.caption(f"Versículo: {r['versiculo']}")
                    if st.button("🗑️ Eliminar", key=f"del_ref_{r['id']}"):
                        delete_reflexion(r['id'])
                        st.rerun()
        else:
            st.info("No hay reflexiones")
    
    # --- ADMIN: CRONICAS ---
    elif admin_option == "📜 Cronicas":
        st.title("📜 Gestionar Crónicas")
        
        with st.form("form_cronica"):
            st.subheader("➕ Nueva Crónica")
            titulo = st.text_input("Título")
            lugar = st.text_input("Lugar")
            estado = st.selectbox("Estado", ["Miranda", "Carabobo", "Distrito Capital", "Zulia", "Lara", "Aragua", "Bolivar", "Anzoategui", "Merida", "Tachira", "Nueva Esparta", "Sucre", "Falcon", "Barinas", "Portuguesa", "Guarico", "Cojedes", "Trujillo", "Yaracuy", "Apure", "Amazonas", "Delta Amacuro", "Vargas"])
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("📜 Guardar"):
                if titulo and contenido:
                    if add_cronica(titulo, contenido, lugar, estado):
                        st.success("✅ Crónica guardada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Complete los campos")
        
        st.markdown("---")
        st.subheader("📋 Crónicas Existentes")
        cronicas = get_cronicas()
        if not cronicas.empty:
            for _, c in cronicas.iterrows():
                with st.expander(f"{c['titulo']} - {c['lugar']}, {c['estado']}"):
                    st.write(c['contenido'])
                    if st.button("🗑️ Eliminar", key=f"del_cron_{c['id']}"):
                        delete_cronica(c['id'])
                        st.rerun()
        else:
            st.info("No hay crónicas")
    
    # --- ADMIN: VIDEOS ---
    elif admin_option == "🎬 Videos":
        st.title("🎬 Gestionar Videos")
        
        with st.form("form_video"):
            st.subheader("➕ Agregar Video (URL)")
            titulo = st.text_input("Título del Video")
            url_video = st.text_input("URL del video", placeholder="https://ejemplo.com/video.mp4 o URL de YouTube")
            if st.form_submit_button("🎬 Agregar Video"):
                if titulo and url_video:
                    if add_video(titulo, url_video):
                        st.success("✅ Video agregado!")
                        st.rerun()
                else:
                    st.warning("⚠️ Complete los campos")
        
        st.markdown("---")
        st.subheader("📋 Videos Existentes")
        videos = get_videos()
        if not videos.empty:
            for _, v in videos.iterrows():
                with st.expander(v['titulo']):
                    st.video(v['video_url'])
                    if st.button("🗑️ Eliminar", key=f"del_vid_{v['id']}"):
                        delete_video(v['id'])
                        st.rerun()
        else:
            st.info("No hay videos")
    
    # --- ADMIN: MUSICA ---
    elif admin_option == "🎵 Musica":
        st.title("🎵 Gestionar Música")
        
        with st.form("form_musica"):
            st.subheader("➕ Agregar Canción (URL)")
            titulo = st.text_input("Título de la Canción")
            url_audio = st.text_input("URL del audio", placeholder="https://ejemplo.com/cancion.mp3")
            if st.form_submit_button("🎵 Agregar Canción"):
                if titulo and url_audio:
                    if add_musica(titulo, url_audio):
                        st.success("✅ Canción agregada!")
                        st.rerun()
                else:
                    st.warning("⚠️ Complete los campos")
        
        st.markdown("---")
        st.subheader("📋 Canciones Existentes")
        musicas = get_musicas()
        if not musicas.empty:
            for _, m in musicas.iterrows():
                with st.expander(m['titulo']):
                    st.audio(m['audio_url'])
                    if st.button("🗑️ Eliminar", key=f"del_mus_{m['id']}"):
                        delete_musica(m['id'])
                        st.rerun()
        else:
            st.info("No hay música")
    
    # --- ADMIN: DENUNCIAS ---
    elif admin_option == "⚠️ Denuncias":
        st.title("⚠️ Gestionar Denuncias")
        
        denuncias = get_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                with st.expander(f"{d['titulo']} - {d['estatus']}"):
                    st.write(f"**Denunciante:** {d['denunciante']}")
                    st.write(f"**Descripción:** {d['descripcion']}")
                    st.write(f"**Ubicación:** {d['ubicacion']}")
                    nuevo_estado = st.selectbox("Estado", ["Pendiente", "En revisión", "Resuelta", "Descartada"], key=f"est_{d['id']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Actualizar", key=f"upd_{d['id']}"):
                            update_denuncia_status(d['id'], nuevo_estado)
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Eliminar", key=f"del_den_{d['id']}"):
                            delete_denuncia(d['id'])
                            st.rerun()
        else:
            st.info("No hay denuncias")
    
    # --- ADMIN: OPINIONES ---
    elif admin_option == "💬 Opiniones":
        st.title("💬 Gestionar Opiniones")
        
        st.subheader("⏳ Pendientes de Aprobar")
        opiniones_pendientes = get_opiniones(aprobadas=False)
        if not opiniones_pendientes.empty:
            for _, op in opiniones_pendientes.iterrows():
                if not op['aprobada']:
                    with st.expander(f"{op['usuario']} - {op['fecha']}"):
                        st.write(op['comentario'])
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Aprobar", key=f"aprob_{op['id']}"):
                                approve_opinion(op['id'])
                                st.rerun()
                        with col2:
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
    
    # --- ADMIN: CONFIGURACION ---
    elif admin_option == "⚙️ Configuracion":
        st.title("⚙️ Configuración")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎨 Logo de la App")
            if logo:
                st.image(logo, width=150)
            nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg"])
            if nuevo_logo and st.button("💾 Guardar Logo"):
                logo_b64 = img_to_base64(nuevo_logo)
                if logo_b64:
                    save_logo(logo_b64)
                    st.success("Logo guardado!")
                    st.rerun()
        
        with col2:
            st.subheader("💰 Dólar BCV")
            st.write(f"Precio actual: {dolar:.2f} Bs/USD")
            nuevo_dolar = st.number_input("Nuevo valor (Bs/USD)", value=float(dolar), step=0.01)
            if st.button("💾 Actualizar Dólar"):
                if actualizar_dolar_manual(nuevo_dolar):
                    st.success(f"Dólar actualizado a {nuevo_dolar:.2f} Bs")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("### 📊 Estadísticas")
            st.metric("Total de Noticias", len(get_noticias()))
            st.metric("Total de Negocios", len(get_negocios()))
            st.metric("Total de Crónicas", len(get_cronicas()))
            st.metric("Total de Denuncias", len(get_denuncias()))

# ============================================
# FOOTER - PLACA DE BRONCE
# ============================================
st.markdown("""
<div class="bronze-footer">
    <div class="screw screw-tl"></div>
    <div class="screw screw-tr"></div>
    <div class="screw screw-bl"></div>
    <div class="screw screw-br"></div>
    <p class="titulo">⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproducción total o parcial</p>
    <p>DERECHOS RESERVADOS</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
