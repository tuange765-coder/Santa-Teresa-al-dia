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
# DETECTAR DISPOSITIVO MOVIL
# ============================================
def is_mobile():
    try:
        user_agent = st.context.headers.get('User-Agent', '').lower()
        mobile_keywords = ['android', 'iphone', 'ipad', 'ipod', 'windows phone', 'mobile', 'blackberry', 'opera mini', 'iemobile']
        return any(keyword in user_agent for keyword in mobile_keywords)
    except:
        return False

es_movil = is_mobile()

# ============================================
# ESTILOS PARA MOVIL
# ============================================
if es_movil:
    st.markdown("""
    <style>
    .main > div {
        padding: 8px !important;
        margin: 5px 0 !important;
    }
    .stButton > button {
        padding: 6px 12px !important;
        font-size: 0.85em !important;
    }
    h1 {
        font-size: 1.4em !important;
    }
    h2, h3 {
        font-size: 1.1em !important;
    }
    .stats-panel {
        padding: 8px !important;
    }
    .streamlit-expanderHeader {
        font-size: 0.85em !important;
        padding: 6px !important;
    }
    [data-testid="stSidebar"] {
        min-width: 220px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# OCULTAR ELEMENTOS DE DESARROLLO
# ============================================
st.markdown("""
<style>
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
.stDeployButton {display: none !important;}
header {visibility: hidden !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
.stAppDeployButton {display: none !important;}
.viewerBadge_container__1QSob {display: none !important;}
.stVersion {display: none !important;}
.stApp > header {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

# ============================================
# URL DE LA APP
# ============================================
APP_URL = "https://santateresaldia.streamlit.app/"

# ============================================
# CONFIGURACION DE PAGINA
# ============================================
st.set_page_config(
    page_title="Santa Teresa al Dia",
    page_icon="🇻🇪",
    layout="wide"
)

# ============================================
# ZONA HORARIA
# ============================================
CARACAS_TZ = pytz.timezone('America/Caracas')

def get_fecha_hora_venezuela():
    ahora_utc = datetime.now(pytz.UTC)
    ahora_caracas = ahora_utc.astimezone(CARACAS_TZ)
    return ahora_caracas

# ============================================
# CONEXION A BASE DE DATOS
# ============================================
def init_connection():
    try:
        if "DATABASE_URL" in st.secrets:
            conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        else:
            st.error("Error de configuracion.")
            st.stop()
        test_query = conn.query("SELECT 1 as test", ttl=0)
        if test_query.empty:
            st.error("Error de conexion.")
            st.stop()
        return conn
    except Exception:
        st.error("Error de conexion.")
        st.stop()

conn = init_connection()

# ============================================
# CREAR TABLAS
# ============================================
def crear_tablas_si_no_existen():
    try:
        with conn.session as s:
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                categoria TEXT,
                contenido TEXT,
                imagen_url TEXT,
                fecha TEXT,
                autor TEXT
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS negocios (
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
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS cronicas (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                contenido TEXT,
                autor TEXT,
                fecha TEXT,
                lugar TEXT,
                estado TEXT
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                video_data TEXT,
                formato TEXT,
                fecha TEXT
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS musicas (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                audio_data TEXT,
                formato TEXT,
                fecha TEXT
            )
            """))
            
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
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY,
                conteo INTEGER DEFAULT 1500
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                logo_url TEXT,
                dolar REAL DEFAULT 489.55
            )
            """))
            
            res = s.execute(text("SELECT COUNT(*) FROM visitas WHERE id = 1")).fetchone()
            if res[0] == 0:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 1500)"))
            
            res2 = s.execute(text("SELECT COUNT(*) FROM configuracion WHERE id = 1")).fetchone()
            if res2[0] == 0:
                s.execute(text("INSERT INTO configuracion (id, logo_url, dolar) VALUES (1, NULL, 489.55)"))
            
            res3 = s.execute(text("SELECT COUNT(*) FROM cronicas")).fetchone()
            if res3[0] == 0:
                cronicas_iniciales = [
                    ("Los Valles del Tuy", "Los Valles del Tuy fueron testigos de importantes batallas por la independencia.", "Cronista", "1781", "Valles del Tuy", "Miranda"),
                    ("La Batalla de Carabobo", "El 24 de junio de 1821, el Ejercito Patriota liderado por Simon Bolivar derroto a las fuerzas realistas.", "Cronista", "1821", "Campo de Carabobo", "Carabobo"),
                    ("Nacimiento del Libertador", "Simon Bolivar nacio en Caracas el 24 de julio de 1783.", "Cronista", "1783", "Caracas", "Distrito Capital")
                ]
                for c in cronicas_iniciales:
                    s.execute(text("INSERT INTO cronicas (titulo, contenido, autor, fecha, lugar, estado) VALUES (:t, :c, :a, :f, :l, :e)"),
                             {"t": c[0], "c": c[1], "a": c[2], "f": c[3], "l": c[4], "e": c[5]})
            
            res4 = s.execute(text("SELECT COUNT(*) FROM reflexiones")).fetchone()
            if res4[0] == 0:
                s.execute(text("""
                    INSERT INTO reflexiones (titulo, contenido, versiculo, autor, fecha, activo)
                    VALUES ('La Paz de Dios', 
                    'No te angusties por nada. Presenta tus peticiones delante de Dios.', 
                    'Filipenses 4:6-7', 
                    'Ministerio', 
                    '2026-01-01', 
                    TRUE)
                """))
            
            res5 = s.execute(text("SELECT COUNT(*) FROM noticias")).fetchone()
            if res5[0] == 0:
                fecha_actual = datetime.now().strftime("%d/%m/%Y")
                noticias_iniciales = [
                    ("Bienvenidos", "Nacional", "Un espacio para mantenernos informados.", fecha_actual, "Admin"),
                    ("Santa Teresa progresa", "Nacional", "Nuestra ciudad sigue creciendo.", fecha_actual, "Admin"),
                    ("Vinotinto se prepara", "Deportes", "La seleccion continua su preparacion.", fecha_actual, "Admin"),
                    ("Panorama global", "Internacional", "Analisis de los principales sucesos.", fecha_actual, "Admin")
                ]
                for n in noticias_iniciales:
                    s.execute(text("INSERT INTO noticias (titulo, categoria, contenido, fecha, autor) VALUES (:t, :c, :cont, :f, :a)"),
                             {"t": n[0], "c": n[1], "cont": n[2], "f": n[3], "a": n[4]})
            
            s.commit()
            return True
    except Exception as e:
        print(f"Error creando tablas: {e}")
        return False

crear_tablas_si_no_existen()

# ============================================
# FUNCIONES DE CONVERSION
# ============================================
def video_a_base64(file):
    if file:
        try:
            bytes_data = file.read()
            if len(bytes_data) > 50 * 1024 * 1024:
                st.error("Video muy grande (maximo 50 MB)")
                return None
            return base64.b64encode(bytes_data).decode()
        except Exception:
            return None
    return None

def audio_a_base64(file):
    if file:
        try:
            bytes_data = file.read()
            if len(bytes_data) > 20 * 1024 * 1024:
                st.error("Audio muy grande (maximo 20 MB)")
                return None
            return base64.b64encode(bytes_data).decode()
        except Exception:
            return None
    return None

def img_a_base64(file):
    if file:
        try:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        except Exception:
            return None
    return None

def mostrar_video(video_data, formato):
    try:
        video_bytes = base64.b64decode(video_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato}") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name
        if es_movil:
            st.video(tmp_path)
        else:
            st.markdown('<div style="max-width: 500px; margin: 0 auto;">', unsafe_allow_html=True)
            st.video(tmp_path)
            st.markdown('</div>', unsafe_allow_html=True)
        os.unlink(tmp_path)
    except Exception:
        st.error("Error al cargar video")

def mostrar_audio(audio_data, formato):
    try:
        audio_bytes = base64.b64decode(audio_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato}") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        st.audio(tmp_path)
        os.unlink(tmp_path)
    except Exception:
        st.error("Error al cargar audio")

# ============================================
# FUNCION DOLAR - CORREGIDA
# ============================================
def get_dolar():
    try:
        with conn.session as s:
            result = s.execute(text("SELECT dolar FROM configuracion WHERE id = 1")).fetchone()
            if result and result[0]:
                return float(result[0])
        return 489.55
    except Exception as e:
        print(f"Error obteniendo dolar: {e}")
        return 489.55

def actualizar_dolar_manual(nuevo_valor):
    try:
        with conn.session as s:
            s.execute(text("UPDATE configuracion SET dolar = :p WHERE id = 1"), {"p": float(nuevo_valor)})
            s.commit()
        return True
    except Exception as e:
        print(f"Error actualizando dolar: {e}")
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
        with conn.session as s:
            result = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
            if result:
                return int(result[0])
        return 1500
    except:
        return 1500

def get_logo():
    try:
        with conn.session as s:
            result = s.execute(text("SELECT logo_url FROM configuracion WHERE id = 1")).fetchone()
            if result and result[0]:
                return result[0]
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

# ============================================
# NOTICIAS
# ============================================
def add_noticia(titulo, categoria, contenido, imagen):
    try:
        ahora = get_fecha_hora_venezuela()
        img_url = img_a_base64(imagen) if imagen else None
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
        img_url = img_a_base64(imagen) if imagen else None
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
def add_video(titulo, archivo_video):
    try:
        ahora = get_fecha_hora_venezuela()
        video_data = video_a_base64(archivo_video)
        if video_data:
            formato = archivo_video.type.split("/")[-1] if archivo_video.type else "mp4"
            with conn.session as s:
                s.execute(text("""
                    INSERT INTO videos (titulo, video_data, formato, fecha)
                    VALUES (:t, :v, :fmt, :f)
                """), {"t": titulo, "v": video_data, "fmt": formato, "f": ahora.strftime("%d/%m/%Y")})
                s.commit()
            return True
        return False
    except Exception:
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
def add_musica(titulo, archivo_audio):
    try:
        ahora = get_fecha_hora_venezuela()
        audio_data = audio_a_base64(archivo_audio)
        if audio_data:
            formato = archivo_audio.type.split("/")[-1] if archivo_audio.type else "mp3"
            with conn.session as s:
                s.execute(text("""
                    INSERT INTO musicas (titulo, audio_data, formato, fecha)
                    VALUES (:t, :a, :fmt, :f)
                """), {"t": titulo, "a": audio_data, "fmt": formato, "f": ahora.strftime("%d/%m/%Y")})
                s.commit()
            return True
        return False
    except Exception:
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
# ESTILOS PRINCIPALES
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
.screw-tl { top: 15px; left: 15px; }
.screw-tr { top: 15px; right: 15px; }
.screw-bl { bottom: 15px; left: 15px; }
.screw-br { bottom: 15px; right: 15px; }
.streamlit-expanderHeader {
    background-color: rgba(0,0,0,0.5);
    border-radius: 10px;
    border-left: 4px solid #FFD700;
    font-weight: bold;
}
.share-row {
    display: flex;
    justify-content: center;
    gap: 15px;
    flex-wrap: wrap;
    margin: 15px 0;
}
.share-btn {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 25px;
    text-align: center;
    text-decoration: none;
    font-weight: bold;
    color: white;
    min-width: 110px;
}
.share-wa { background: #25D366; }
.share-fb { background: #1877F2; }
.share-ig { background: linear-gradient(45deg, #f09433, #d62976); }
.share-copy { background: #3498db; }
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(0,0,0,0.5);
    border-radius: 15px;
    padding: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: rgba(0,0,0,0.7);
    border-radius: 12px;
    color: #FFD700 !important;
    font-weight: bold;
    padding: 10px 25px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #FFD700, #CF142B) !important;
    color: white !important;
}
.download-guide {
    background: linear-gradient(135deg, #1a472a, #0d2818);
    border: 2px solid #FFD700;
    border-radius: 20px;
    padding: 20px;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# FECHA Y HORA
# ============================================
ahora = get_fecha_hora_venezuela()
dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# ============================================
# LOGO
# ============================================
logo = get_logo()
if logo:
    st.markdown(f'<div style="text-align: center;"><img src="{logo}" style="max-width: 200px;"></div>', unsafe_allow_html=True)

# ============================================
# ENCABEZADO CON FOTO DE FONDO - CORREGIDO
# ============================================
# URL de una imagen real de Santa Teresa del Tuy (IMAGEN REAL DE VENEZUELA)
# Usando una imagen de referencia de los Valles del Tuy
fondo_santa_teresa_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Valles_del_Tuy.jpg/1200px-Valles_del_Tuy.jpg"

# Si la imagen anterior no carga, usar esta imagen de respaldo de Venezuela
fondo_respaldo = "https://images.unsplash.com/photo-1580397583982-7a5c6f6b6f6b?w=1200"

st.markdown(f"""
<div style="text-align: center; margin-bottom: 20px;">
    <div style="background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), 
                url('https://images.pexels.com/photos/1658967/pexels-photo-1658967.jpeg?auto=compress&cs=tinysrgb&w=1200');
                background-size: cover;
                background-position: center;
                border-radius: 20px;
                padding: 60px 20px;
                border: 3px solid #FFD700;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <h1 style="color: white; text-shadow: 3px 3px 8px black; font-size: 2.5em;">🇻🇪 Santa Teresa al Día 🇻🇪</h1>
        <p style="color: #FFD700; text-shadow: 2px 2px 4px black; font-size: 1.2em;">Información, Cultura y Fe | Santa Teresa del Tuy, Miranda</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# BOTONES DE COMPARTIR
# ============================================
st.markdown(f"""
<div class="share-row">
    <a href="https://api.whatsapp.com/send?text=Santa Teresa al Dia - {APP_URL}" target="_blank" class="share-btn share-wa">📱 WhatsApp</a>
    <a href="https://www.facebook.com/sharer/sharer.php?u={APP_URL}" target="_blank" class="share-btn share-fb">📘 Facebook</a>
    <button onclick="copyToClipboard('{APP_URL}')" class="share-btn share-ig">📸 Instagram</button>
    <button onclick="copyToClipboard('{APP_URL}')" class="share-btn share-copy">📋 Copiar</button>
</div>
<script>
function copyToClipboard(text) {{
    navigator.clipboard.writeText(text);
    alert("✅ Enlace copiado!");
}}
</script>
""", unsafe_allow_html=True)

st.markdown("---")

# ============================================
# PANEL SUPERIOR
# ============================================
st.markdown(f"""
<div class="stats-panel">
    <span style="color:#FFD700;">⭐ {dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year} ⭐</span><br>
    <span style="color:white; font-size:1.5em;">{ahora.strftime("%I:%M %p")}</span><br>
    <span style="color:#FFD700;">👥 Visitantes: {visitas:,} | 💵 Dolar BCV: {dolar:.2f} Bs</span>
</div>
""", unsafe_allow_html=True)

# ============================================
# GUIA PARA INSTALAR APP EN MOVIL
# ============================================
if es_movil:
    with st.expander("📱 **¿Cómo instalar esta app en tu móvil?**", expanded=False):
        st.markdown("""
        <div class="download-guide">
            <h3 style="color:#FFD700; text-align:center;">📲 Instalar App en tu Teléfono</h3>
            <p style="text-align:center;">Sigue estos pasos para usar Santa Teresa al Día como una app nativa:</p>
            
            <div style="background:rgba(0,0,0,0.5); border-radius:15px; padding:15px; margin:15px 0;">
                <h4 style="color:#FFD700;">🤖 Android (Chrome)</h4>
                <ol>
                    <li>Abre Chrome y ve a <code>santateresaldia.streamlit.app</code></li>
                    <li>Toca los 3 puntitos ⋮ en la esquina superior derecha</li>
                    <li>Selecciona <strong>"Instalar aplicación"</strong> o <strong>"Agregar a pantalla de inicio"</strong></li>
                    <li>Confirma tocando <strong>"Instalar"</strong></li>
                    <li>✅ ¡Listo! La app aparecerá en tu pantalla de inicio</li>
                </ol>
            </div>
            
            <div style="background:rgba(0,0,0,0.5); border-radius:15px; padding:15px; margin:15px 0;">
                <h4 style="color:#FFD700;">🍎 iPhone / iPad (Safari)</h4>
                <ol>
                    <li>Abre Safari y ve a <code>santateresaldia.streamlit.app</code></li>
                    <li>Toca el botón de compartir 📤 (cuadro con flecha arriba)</li>
                    <li>Desplázate y selecciona <strong>"Agregar a pantalla de inicio"</strong></li>
                    <li>Toca <strong>"Agregar"</strong> en la esquina superior derecha</li>
                    <li>✅ ¡Listo! La app se instalará como un icono en tu iPhone</li>
                </ol>
            </div>
            
            <div style="text-align:center; margin-top:15px;">
                <a href="{APP_URL}" target="_blank" style="background:#FFD700; color:#000; padding:10px 20px; border-radius:25px; text-decoration:none; font-weight:bold;">
                    🌐 Abrir la Web App
                </a>
            </div>
            <p style="text-align:center; margin-top:10px;">✨ <strong>Beneficios:</strong> Acceso rápido, funciona offline (parcial), ícono en pantalla de inicio</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================
# SIDEBAR - PANEL DE ADMINISTRACION
# ============================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", width=150)
    st.markdown("---")
    
    # Panel de Administración
    st.markdown("### 🔐 Administración")
    clave = st.text_input("Clave de acceso:", type="password", key="admin_pass")
    
    es_admin = False
    if clave == "Juan*316*" or clave == "1966":
        es_admin = True
        st.success("✅ Acceso concedido")
    elif clave:
        st.error("❌ Clave incorrecta")
    
    if es_admin:
        st.markdown("---")
        st.markdown("### 📋 Panel de Control")
        
        admin_opt = st.radio("Seleccionar módulo:", [
            "📰 Noticias", "🏪 Negocios", "💭 Reflexiones", "📜 Crónicas",
            "🎬 Videos", "🎵 Música", "⚠️ Denuncias", "💬 Opiniones", "⚙️ Configuración"
        ])
        
        st.session_state.admin_opt = admin_opt
        st.session_state.es_admin = True
    else:
        st.session_state.es_admin = False

# ============================================
# MENU PRINCIPAL EN LA PARTE SUPERIOR (TABS)
# ============================================
menu_tabs = st.tabs(["🏠 Portada", "📰 Noticias", "📍 Donde ir - Donde comprar", "💭 Reflexiones", "📜 Crónicas", "🎬 Multimedia", "⚠️ Denuncias", "💬 Opiniones", "📅 Efemérides Médicas"])

# ============================================
# CONTENIDO DE CADA TAB
# ============================================

# --- TAB 0: PORTADA ---
with menu_tabs[0]:
    st.title("🏠 Santa Teresa al Dia")
    
    st.markdown("### 📰 Últimas Noticias")
    noticias = get_noticias()
    if not noticias.empty:
        for _, n in noticias.head(10).iterrows():
            with st.expander(f"{n['titulo']} - {n['categoria']} ({n['fecha']})"):
                if n['imagen_url']:
                    st.image(n['imagen_url'], width=300)
                st.write(n['contenido'])
    else:
        st.info("No hay noticias")
    
    st.markdown("---")
    st.markdown("### ✝️ Reflexión del Día")
    ref = get_reflexion_activa()
    if ref is not None:
        with st.expander(f"{ref['titulo']}", expanded=True):
            st.write(ref['contenido'])
            st.caption(f"📖 {ref['versiculo']}")
    else:
        st.info("No hay reflexión activa")
    
    st.markdown("---")
    st.markdown("### ⭐ Recomendados")
    negocios = get_negocios()
    if not negocios.empty:
        for _, n in negocios.head(3).iterrows():
            st.markdown(f"**🏪 {n['nombre']}** - {n['categoria']}")

# --- TAB 1: NOTICIAS ---
with menu_tabs[1]:
    st.title("📰 Noticias")
    
    tab_nac, tab_inter, tab_dep = st.tabs(["🇻🇪 Nacionales", "🌎 Internacionales", "⚽ Deportes"])
    
    with tab_nac:
        noticias_nac = get_noticias(categoria="Nacional")
        if not noticias_nac.empty:
            for _, n in noticias_nac.iterrows():
                with st.expander(f"{n['titulo']} - {n['fecha']}"):
                    if n['imagen_url']:
                        st.image(n['imagen_url'], width=300)
                    st.write(n['contenido'])
        else:
            st.info("No hay noticias Nacionales")
    
    with tab_inter:
        noticias_inter = get_noticias(categoria="Internacional")
        if not noticias_inter.empty:
            for _, n in noticias_inter.iterrows():
                with st.expander(f"{n['titulo']} - {n['fecha']}"):
                    if n['imagen_url']:
                        st.image(n['imagen_url'], width=300)
                    st.write(n['contenido'])
        else:
            st.info("No hay noticias Internacionales")
    
    with tab_dep:
        noticias_dep = get_noticias(categoria="Deportes")
        if not noticias_dep.empty:
            for _, n in noticias_dep.iterrows():
                with st.expander(f"{n['titulo']} - {n['fecha']}"):
                    if n['imagen_url']:
                        st.image(n['imagen_url'], width=300)
                    st.write(n['contenido'])
        else:
            st.info("No hay noticias de Deportes")

# --- TAB 2: DONDE IR - DONDE COMPRAR ---
with menu_tabs[2]:
    st.title("📍 Donde ir - Donde comprar")
    
    negocios = get_negocios()
    if not negocios.empty:
        for _, n in negocios.iterrows():
            col_a, col_b = st.columns([1, 2])
            with col_a:
                if n['imagen_url']:
                    st.image(n['imagen_url'], use_container_width=True)
                else:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Flag_of_Venezuela_%28state%29.svg/1200px-Flag_of_Venezuela_%28state%29.svg.png", use_container_width=True)
            with col_b:
                st.markdown(f"### {n['nombre']}")
                st.caption(n['categoria'])
                st.write(n['resena'])
                if n['direccion']:
                    st.write(f"📍 **Dirección:** {n['direccion']}")
                if n['telefono']:
                    st.write(f"📞 **Teléfono:** {n['telefono']}")
                if n['horario']:
                    st.write(f"⏰ **Horario:** {n['horario']}")
            st.markdown("---")
    else:
        st.info("No hay negocios agregados")

# --- TAB 3: REFLEXIONES ---
with menu_tabs[3]:
    st.title("💭 Reflexiones")
    
    ref = get_reflexion_activa()
    if ref is not None:
        with st.expander(f"✨ ACTUAL: {ref['titulo']}", expanded=True):
            st.write(ref['contenido'])
            st.caption(f"📖 {ref['versiculo']}")
            st.caption(f"📅 {ref['fecha']}")
    else:
        st.info("No hay reflexión activa")
    
    st.markdown("---")
    st.markdown("### 📜 Reflexiones Anteriores")
    reflexiones = get_reflexiones()
    if not reflexiones.empty:
        for _, r in reflexiones.iterrows():
            if ref is None or r['id'] != ref['id']:
                with st.expander(f"{r['titulo']} - {r['fecha']}"):
                    st.write(r['contenido'])
                    if r['versiculo']:
                        st.caption(f"📖 {r['versiculo']}")
    else:
        st.info("No hay reflexiones anteriores")

# --- TAB 4: CRONICAS ---
with menu_tabs[4]:
    st.title("📜 Crónicas")
    
    estados = ["Todos", "Miranda", "Carabobo", "Distrito Capital", "Zulia", "Lara", "Aragua", "Bolivar", "Anzoategui", "Merida", "Tachira", "Nueva Esparta", "Sucre", "Falcon", "Barinas", "Portuguesa", "Guarico", "Cojedes", "Trujillo", "Yaracuy", "Apure", "Amazonas", "Delta Amacuro", "Vargas"]
    estado_filtro = st.selectbox("Filtrar por estado:", estados)
    
    cronicas = get_cronicas(estado_filtro if estado_filtro != "Todos" else None)
    if not cronicas.empty:
        for _, c in cronicas.iterrows():
            with st.expander(f"📖 {c['titulo']} - {c['lugar']}, {c['estado']}"):
                st.write(c['contenido'])
                st.caption(f"📅 {c['fecha']}")
    else:
        st.info("No hay crónicas disponibles")

# --- TAB 5: MULTIMEDIA ---
with menu_tabs[5]:
    st.title("🎬 Multimedia")
    
    tab_vid, tab_mus, tab_rad = st.tabs(["🎥 Videos", "🎵 Música", "📻 Radio"])
    
    with tab_vid:
        videos = get_videos()
        if not videos.empty:
            for _, v in videos.iterrows():
                with st.expander(f"🎬 {v['titulo']}"):
                    mostrar_video(v['video_data'], v['formato'])
                    st.caption(f"Subido: {v['fecha']}")
        else:
            st.info("No hay videos disponibles")
    
    with tab_mus:
        musicas = get_musicas()
        if not musicas.empty:
            for _, m in musicas.iterrows():
                with st.expander(f"🎵 {m['titulo']}"):
                    mostrar_audio(m['audio_data'], m['formato'])
                    st.caption(f"Agregado: {m['fecha']}")
        else:
            st.info("No hay música disponible")
    
    with tab_rad:
        st.markdown("### 📻 Radio Online")
        st.audio("https://streaming.radiosenlinea.net/9090/stream")

# --- TAB 6: DENUNCIAS ---
with menu_tabs[6]:
    st.title("⚠️ Denuncias Ciudadanas")
    
    tab_den, tab_ver = st.tabs(["📝 Hacer Denuncia", "👁️ Ver Denuncias"])
    
    with tab_den:
        with st.form("fd"):
            nombre = st.text_input("Nombre (opcional)")
            titulo = st.text_input("Título *")
            desc = st.text_area("Descripción *")
            ubic = st.text_input("Ubicación")
            if st.form_submit_button("📤 Enviar Denuncia"):
                if titulo and desc:
                    add_denuncia(nombre, titulo, desc, ubic)
                    st.success("✅ Denuncia enviada correctamente")
                    st.balloons()
                else:
                    st.error("❌ Título y descripción son obligatorios")
    
    with tab_ver:
        denuncias = get_denuncias()
        if not denuncias.empty:
            for _, d in denuncias.iterrows():
                st.markdown(f"**📌 {d['titulo']}** - `{d['estatus']}`")
                st.caption(f"📍 {d['ubicacion'] if d['ubicacion'] else 'No especificada'}")
                with st.expander("Ver detalles"):
                    st.write(d['descripcion'])
                    st.caption(f"📅 {d['fecha']}")
                st.divider()
        else:
            st.info("No hay denuncias registradas")

# --- TAB 7: OPINIONES ---
with menu_tabs[7]:
    st.title("💬 Opiniones")
    
    tab_op, tab_ver_op = st.tabs(["✍️ Dar Opinión", "👁️ Ver Opiniones"])
    
    with tab_op:
        with st.form("fo"):
            usuario = st.text_input("Nombre *")
            comentario = st.text_area("Comentario *")
            estrellas = st.slider("Calificación", 1, 5, 5)
            if st.form_submit_button("📤 Enviar Opinión"):
                if usuario and comentario:
                    add_opinion(usuario, comentario, estrellas)
                    st.success("✅ Opinión enviada, será revisada por un administrador")
                    st.balloons()
                else:
                    st.error("❌ Nombre y comentario son obligatorios")
    
    with tab_ver_op:
        opiniones = get_opiniones(aprobadas=True)
        if not opiniones.empty:
            for _, op in opiniones.iterrows():
                stars = "⭐" * int(op['calificacion']) + "☆" * (5 - int(op['calificacion']))
                st.markdown(f"**👤 {op['usuario']}** {stars}")
                st.write(f"\"{op['comentario']}\"")
                st.caption(f"📅 {op['fecha']}")
                st.divider()
        else:
            st.info("No hay opiniones aprobadas")

# ============================================
# TAB 8: EFEMÉRIDES MÉDICAS - CORREGIDO
# ============================================
with menu_tabs[8]:
    st.title("📅 Efemérides Médicas")
    
    # Formato correcto de fecha para comparación
    dia_actual = ahora.day
    mes_actual = meses[ahora.month-1]
    fecha_actual_str = f"{dia_actual} de {mes_actual}"
    
    st.markdown(f"""
    <div style="text-align:center; background:rgba(0,0,0,0.5); border-radius:15px; padding:20px; margin-bottom:20px;">
        <h2 style="color:#FFD700;">📌 {dias[ahora.weekday()]}, {fecha_actual_str} de {ahora.year}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col_ven, col_mundo = st.columns(2)
    
    # ========== EFEMÉRIDES DE VENEZUELA ==========
    with col_ven:
        st.markdown("### 🇻🇪 Efemérides de Venezuela")
        
        # Diccionario con TODAS las efemérides venezolanas
        efemerides_venezuela = {
            "13 de Octubre": "Día del Trabajador de la Salud en Venezuela",
            "24 de Junio": "Día del Médico Venezolano - Nacimiento del Dr. José María Vargas",
            "3 de Diciembre": "Día del Odontólogo Venezolano",
            "10 de Diciembre": "Día de la Enfermera Venezolana",
            "12 de Mayo": "Día de la Madre (vinculado a la salud familiar)",
            "12 de Marzo": "Día del Oftalmólogo Venezolano",
            "15 de Abril": "Día del Bioanalista Venezolano",
            "11 de Mayo": "Día de la Enfermera Venezolana",
            "22 de Noviembre": "Día del Farmacéutico Venezolano"
        }
        
        # Buscar efeméride para hoy
        efemeride_hoy_ven = None
        for fecha in efemerides_venezuela:
            if fecha.lower() == fecha_actual_str.lower():
                efemeride_hoy_ven = efemerides_venezuela[fecha]
                break
        
        # Mostrar resultado
        if efemeride_hoy_ven:
            st.success(f"""
            ### 🎉 ¡EFEMÉRIDE DEL DÍA!
            **{fecha_actual_str}**\n
            {efemeride_hoy_ven}
            """)
        else:
            st.info(f"📌 Para hoy **{fecha_actual_str}** no hay una efeméride médica registrada en Venezuela.")
        
        st.markdown("---")
        st.markdown("#### 📅 Calendario de efemérides médicas en Venezuela:")
        
        for fecha in sorted(efemerides_venezuela.keys()):
            if fecha.lower() != fecha_actual_str.lower():
                st.markdown(f"**{fecha}:** {efemerides_venezuela[fecha]}")
    
    # ========== EFEMÉRIDES DEL MUNDO ==========
    with col_mundo:
        st.markdown("### 🌎 Efemérides del Mundo")
        
        # Diccionario con TODAS las efemérides mundiales
        efemerides_mundo = {
            "12 de Mayo": "Día Internacional de la Enfermería (natalicio de Florence Nightingale)",
            "6 de Abril": "Día Mundial de la Actividad Física",
            "7 de Abril": "Día Mundial de la Salud",
            "31 de Mayo": "Día Mundial sin Tabaco",
            "14 de Junio": "Día Mundial del Donante de Sangre",
            "28 de Julio": "Día Mundial contra la Hepatitis",
            "8 de Septiembre": "Día Mundial de la Fisioterapia",
            "10 de Octubre": "Día Mundial de la Salud Mental",
            "14 de Noviembre": "Día Mundial de la Diabetes",
            "1 de Diciembre": "Día Mundial de la Lucha contra el Sida",
            "17 de Mayo": "Día Mundial de la Hipertensión",
            "21 de Junio": "Día Mundial de la ELA (Esclerosis Lateral Amiotrófica)",
            "29 de Septiembre": "Día Mundial del Corazón",
            "13 de Febrero": "Día Mundial de la Radio (contenidos de salud)"
        }
        
        # Buscar efeméride para hoy
        efemeride_hoy_mundo = None
        for fecha in efemerides_mundo:
            if fecha.lower() == fecha_actual_str.lower():
                efemeride_hoy_mundo = efemerides_mundo[fecha]
                break
        
        # Mostrar resultado
        if efemeride_hoy_mundo:
            st.success(f"""
            ### 🎉 ¡EFEMÉRIDE DEL DÍA!
            **{fecha_actual_str}**\n
            {efemeride_hoy_mundo}
            """)
        else:
            st.info(f"📌 Para hoy **{fecha_actual_str}** no hay una efeméride médica mundial registrada.")
        
        st.markdown("---")
        st.markdown("#### 📅 Calendario de efemérides médicas mundiales:")
        
        for fecha in sorted(efemerides_mundo.keys()):
            if fecha.lower() != fecha_actual_str.lower():
                st.markdown(f"**{fecha}:** {efemerides_mundo[fecha]}")
    
    # Fuentes
    st.markdown("---")
    st.caption("📚 **Fuentes:** Federación Médica Venezolana, Organización Mundial de la Salud (OMS), Sociedades Científicas Internacionales")

# ============================================
# PANEL ADMIN - CONTENIDO
# ============================================
if st.session_state.get('es_admin', False):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Acciones disponibles")
    
    admin_opt = st.session_state.get('admin_opt', "📰 Noticias")
    
    # Mostrar el contenido del panel admin en el área principal
    st.title("🔧 Panel de Administración")
    
    if "📰 Noticias" in admin_opt:
        st.subheader("📰 Gestionar Noticias")
        with st.form("fn"):
            titulo = st.text_input("Título")
            categoria = st.selectbox("Categoría", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido")
            imagen = st.file_uploader("Imagen", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("📤 Publicar Noticia"):
                if titulo and contenido:
                    add_noticia(titulo, categoria, contenido, imagen)
                    st.success("✅ Noticia publicada correctamente")
                    st.rerun()
                else:
                    st.error("❌ Título y contenido son obligatorios")
        
        st.markdown("---")
        st.markdown("### 📋 Noticias existentes")
        for _, n in get_noticias().iterrows():
            with st.expander(f"{n['titulo']} - {n['categoria']}"):
                st.write(n['contenido'])
                if st.button("🗑️ Eliminar", key=f"del_{n['id']}"):
                    delete_noticia(n['id'])
                    st.success("✅ Noticia eliminada")
                    st.rerun()
    
    elif "🏪 Negocios" in admin_opt:
        st.subheader("🏪 Gestionar Negocios")
        with st.form("fneg"):
            nombre = st.text_input("Nombre del negocio")
            categoria = st.text_input("Categoría")
            resena = st.text_area("Reseña")
            direccion = st.text_input("Dirección")
            telefono = st.text_input("Teléfono")
            horario = st.text_input("Horario")
            imagen = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("➕ Agregar Negocio"):
                if nombre and resena:
                    add_negocio(nombre, categoria, resena, direccion, telefono, horario, imagen)
                    st.success("✅ Negocio agregado correctamente")
                    st.rerun()
                else:
                    st.error("❌ Nombre y reseña son obligatorios")
        
        st.markdown("---")
        st.markdown("### 📋 Negocios existentes")
        for _, n in get_negocios().iterrows():
            with st.expander(f"{n['nombre']} - {n['categoria']}"):
                st.write(n['resena'])
                if st.button("🗑️ Eliminar", key=f"del_neg_{n['id']}"):
                    delete_negocio(n['id'])
                    st.success("✅ Negocio eliminado")
                    st.rerun()
    
    elif "💭 Reflexiones" in admin_opt:
        st.subheader("💭 Gestionar Reflexiones")
        with st.form("fref"):
            titulo = st.text_input("Título")
            versiculo = st.text_input("Versículo")
            contenido = st.text_area("Contenido")
            if st.form_submit_button("💾 Guardar Reflexión (activa)"):
                if titulo and contenido:
                    add_reflexion(titulo, contenido, versiculo)
                    st.success("✅ Reflexión guardada como activa")
                    st.rerun()
                else:
                    st.error("❌ Título y contenido son obligatorios")
        
        st.markdown("---")
        st.markdown("### 📋 Reflexiones anteriores")
        for _, r in get_reflexiones().iterrows():
            with st.expander(f"{r['titulo']} - {r['fecha']}"):
                st.write(r['contenido'])
                if r['versiculo']:
                    st.caption(f"📖 {r['versiculo']}")
                if st.button("🗑️ Eliminar", key=f"del_ref_{r['id']}"):
                    delete_reflexion(r['id'])
                    st.success("✅ Reflexión eliminada")
                    st.rerun()
    
    elif "📜 Crónicas" in admin_opt:
        st.subheader("📜 Gestionar Crónicas")
        with st.form("fcro"):
            titulo = st.text_input("Título")
            lugar = st.text_input("Lugar")
            estado = st.selectbox("Estado", ["Miranda", "Carabobo", "Distrito Capital", "Zulia", "Lara", "Aragua", "Bolivar", "Anzoategui", "Merida", "Tachira", "Nueva Esparta", "Sucre", "Falcon", "Barinas", "Portuguesa", "Guarico", "Cojedes", "Trujillo", "Yaracuy", "Apure", "Amazonas", "Delta Amacuro", "Vargas"])
            contenido = st.text_area("Contenido")
            if st.form_submit_button("💾 Guardar Crónica"):
                if titulo and contenido:
                    add_cronica(titulo, contenido, lugar, estado)
                    st.success("✅ Crónica guardada correctamente")
                    st.rerun()
                else:
                    st.error("❌ Título y contenido son obligatorios")
        
        st.markdown("---")
        st.markdown("### 📋 Crónicas existentes")
        for _, c in get_cronicas().iterrows():
            with st.expander(f"{c['titulo']} - {c['lugar']}"):
                st.write(c['contenido'])
                if st.button("🗑️ Eliminar", key=f"del_cron_{c['id']}"):
                    delete_cronica(c['id'])
                    st.success("✅ Crónica eliminada")
                    st.rerun()
    
    elif "🎬 Videos" in admin_opt:
        st.subheader("🎬 Gestionar Videos")
        with st.form("fvid"):
            titulo = st.text_input("Título del video")
            archivo = st.file_uploader("Archivo de video", type=["mp4", "avi", "mov", "mkv"])
            if st.form_submit_button("📤 Subir Video"):
                if titulo and archivo:
                    add_video(titulo, archivo)
                    st.success("✅ Video subido correctamente")
                    st.rerun()
                else:
                    st.error("❌ Título y archivo son obligatorios")
        
        st.markdown("---")
        st.markdown("### 📋 Videos existentes")
        for _, v in get_videos().iterrows():
            with st.expander(v['titulo']):
                mostrar_video(v['video_data'], v['formato'])
                if st.button("🗑️ Eliminar", key=f"del_vid_{v['id']}"):
                    delete_video(v['id'])
                    st.success("✅ Video eliminado")
                    st.rerun()
    
    elif "🎵 Música" in admin_opt:
        st.subheader("🎵 Gestionar Música")
        with st.form("fmus"):
            titulo = st.text_input("Título de la canción")
            archivo = st.file_uploader("Archivo de audio", type=["mp3", "wav", "ogg"])
            if st.form_submit_button("📤 Subir Audio"):
                if titulo and archivo:
                    add_musica(titulo, archivo)
                    st.success("✅ Audio subido correctamente")
                    st.rerun()
                else:
                    st.error("❌ Título y archivo son obligatorios")
        
        st.markdown("---")
        st.markdown("### 📋 Archivos de música")
        for _, m in get_musicas().iterrows():
            with st.expander(m['titulo']):
                mostrar_audio(m['audio_data'], m['formato'])
                if st.button("🗑️ Eliminar", key=f"del_mus_{m['id']}"):
                    delete_musica(m['id'])
                    st.success("✅ Audio eliminado")
                    st.rerun()
    
    elif "⚠️ Denuncias" in admin_opt:
        st.subheader("⚠️ Gestionar Denuncias")
        for _, d in get_denuncias().iterrows():
            with st.expander(f"📌 {d['titulo']} - {d['estatus']}"):
                st.write(f"**Denunciante:** {d['denunciante']}")
                st.write(f"**Descripción:** {d['descripcion']}")
                st.write(f"**Ubicación:** {d['ubicacion'] if d['ubicacion'] else 'No especificada'}")
                nuevo = st.selectbox("Cambiar estado:", ["Pendiente", "En revisión", "Resuelta", "Descartada"], 
                                    index=["Pendiente", "En revisión", "Resuelta", "Descartada"].index(d['estatus']), 
                                    key=f"est_{d['id']}")
                if st.button("✅ Actualizar", key=f"upd_{d['id']}"):
                    update_denuncia_status(d['id'], nuevo)
                    st.success("✅ Estado actualizado")
                    st.rerun()
                if st.button("🗑️ Eliminar", key=f"del_den_{d['id']}"):
                    delete_denuncia(d['id'])
                    st.success("✅ Denuncia eliminada")
                    st.rerun()
    
    elif "💬 Opiniones" in admin_opt:
        st.subheader("💬 Gestionar Opiniones")
        st.markdown("### ⏳ Opiniones pendientes de aprobar")
        for _, op in get_opiniones(aprobadas=False).iterrows():
            if not op['aprobada']:
                with st.expander(f"👤 {op['usuario']} - {op['calificacion']}⭐"):
                    st.write(f"**Comentario:** {op['comentario']}")
                    st.caption(f"📅 {op['fecha']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Aprobar", key=f"aprob_{op['id']}"):
                            approve_opinion(op['id'])
                            st.success("✅ Opinión aprobada")
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Eliminar", key=f"del_op_{op['id']}"):
                            delete_opinion(op['id'])
                            st.success("✅ Opinión eliminada")
                            st.rerun()
        
        st.markdown("---")
        st.markdown("### ✅ Opiniones aprobadas")
        for _, op in get_opiniones(aprobadas=True).iterrows():
            with st.expander(f"👤 {op['usuario']} - {op['calificacion']}⭐"):
                st.write(f"**Comentario:** {op['comentario']}")
                st.caption(f"📅 {op['fecha']}")
                if st.button("🗑️ Eliminar", key=f"del_op_aprob_{op['id']}"):
                    delete_opinion(op['id'])
                    st.success("✅ Opinión eliminada")
                    st.rerun()
    
    elif "⚙️ Configuración" in admin_opt:
        st.subheader("⚙️ Configuración del Sistema")
        
        st.markdown("### 💵 Tipo de Cambio Dólar BCV")
        st.write(f"Valor actual: **{dolar:.2f} Bs**")
        nuevo_dolar = st.number_input("Nuevo valor:", value=float(dolar), step=0.01, format="%.2f")
        
        if st.button("💾 Actualizar Dólar", key="update_dolar_btn"):
            if actualizar_dolar_manual(nuevo_dolar):
                st.success(f"✅ Valor del dólar actualizado a {nuevo_dolar:.2f} Bs")
                st.rerun()
            else:
                st.error("❌ Error al actualizar el valor del dólar")
        
        st.markdown("---")
        st.markdown("### 🖼️ Logo de la aplicación")
        if logo:
            st.image(logo, width=150)
        nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg", "jpeg"])
        if nuevo_logo and st.button("💾 Guardar Logo"):
            b64 = img_a_base64(nuevo_logo)
            if b64:
                save_logo(b64)
                st.success("✅ Logo guardado correctamente")
                st.rerun()

# ============================================
# FOOTER
# ============================================
st.markdown("""
<div class="bronze-footer">
    <div class="screw screw-tl"></div>
    <div class="screw screw-tr"></div>
    <div class="screw screw-bl"></div>
    <div class="screw screw-br"></div>
    <p class="titulo">DESARROLLADO POR WILLIAN ALMENAR</p>
    <p>Prohibida la reproducción total o parcial</p>
    <p>DERECHOS RESERVADOS</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
