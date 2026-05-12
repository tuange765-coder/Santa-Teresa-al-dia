import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image
import base64
import io
import uuid
import random
import pyperclip

# --- CONFIGURACION ---
st.set_page_config(page_title="Guia Comercial Almenar", layout="wide", page_icon="🚀")

# --- DETECTAR SI ES DISPOSITIVO MOVIL ---
def is_mobile():
    """Detecta si el usuario accede desde un dispositivo móvil"""
    try:
        user_agent = st.context.headers.get('User-Agent', '').lower()
        mobile_keywords = ['android', 'iphone', 'ipad', 'ipod', 'windows phone', 'mobile']
        return any(keyword in user_agent for keyword in mobile_keywords)
    except:
        return False

es_movil = is_mobile()

# --- OBTENER URL DE LA APP ---
def get_app_url():
    """Obtiene la URL actual de la aplicación"""
    try:
        headers = st.context.headers
        if headers:
            if 'X-Forwarded-Host' in headers:
                return f"https://{headers['X-Forwarded-Host']}"
            if 'Host' in headers:
                host = headers['Host']
                if 'localhost' in host or '127.0.0.1' in host:
                    return f"http://{host}"
                return f"https://{host}"
    except:
        pass
    return "https://guia-comercial-almenar.streamlit.app"

# --- FUNCION PARA COPIAR AL PORTAPAPELES ---
def copy_to_clipboard(text):
    """Copia texto al portapapeles"""
    try:
        pyperclip.copy(text)
        return True
    except:
        st.markdown(f"""
        <script>
        function copyToClipboard() {{
            navigator.clipboard.writeText("{text}");
        }}
        copyToClipboard();
        </script>
        """, unsafe_allow_html=True)
        return True

# --- CONEXION A NEON (POSTGRESQL) ---
conn = None

try:
    if "DATABASE_URL" in st.secrets:
        conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
    elif "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
        conn = st.connection("postgresql", type="sql")
    else:
        st.error("""
        No se encontro configuracion de base de datos.
        
        Por favor, configura los secrets en Streamlit Cloud:
        
        1. Ve a Settings -> Secrets
        2. Agrega:
        
        DATABASE_URL = "postgresql://usuario:contraseña@host/database?sslmode=require"
        """)
        st.stop()
    
    test_query = conn.query("SELECT 1 as test", ttl=0)
    if test_query.empty:
        st.error("No se pudo verificar la conexion a la base de datos")
        st.stop()
        
except Exception as e:
    st.error(f"Error de conexion: {str(e)}")
    st.stop()

# --- CATEGORIAS DEFINIDAS ---
CAT_LIST = [
    "Salud", "Laboratorios", "Opticas", "Farmacias", "Dulcerias",
    "Comida Rapida", "Panaderias", "Charcuterias", "Carnicerias",
    "Ferreterias", "Zapaterias", "Electrodomesticos", "Fibras Opticas",
    "Taxis", "Mototaxis", "Servicios", "Entes Publicos", "Comercio", "Otros"
]

# --- FUNCION PARA AGREGAR COMERCIOS PREDETERMINADOS ---
def agregar_comercios_predeterminados():
    """Agrega los comercios y entes publicos solicitados si no existen"""
    try:
        with conn.session as s:
            negocios_existentes = s.execute(text("""
                SELECT COUNT(*) FROM comercios 
                WHERE nombre IN ('Corpoelec - Oficina Comercial', 'Fiscalia Municipal', 'Policia Municipal', 
                                'IAPEM', 'CICPC - Delegacion Municipal', 'Tribunales de Santa Teresa', 
                                'Hidrocapital - Oficina Comercial', 'Unicasa', 'Traki', 'La Total', 
                                'El Castillo', 'El Palacio del Blumer')
            """)).fetchone()
            
            if negocios_existentes[0] == 0:
                comercios_predeterminados = [
                    {"nombre": "Corpoelec - Oficina Comercial", "categoria": "Entes Publicos", "ubicacion": "Av. Bolivar, Centro Comercial Santa Teresa, Local 2", "resenna": "Oficina comercial de Corpoelec. Atencion al publico para tramites de luz.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.234167,-66.664722"},
                    {"nombre": "Fiscalia Municipal", "categoria": "Entes Publicos", "ubicacion": "Calle Miranda, Edificio Fiscalia", "resenna": "Sede de la Fiscalia Municipal. Atencion al publico.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.233333,-66.666667"},
                    {"nombre": "Policia Municipal", "categoria": "Entes Publicos", "ubicacion": "Av. Intercomunal, Sector La Esperanza", "resenna": "Comando de la Policia Municipal. Seguridad ciudadana.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.235000,-66.665000"},
                    {"nombre": "IAPEM", "categoria": "Entes Publicos", "ubicacion": "Av. Principal, Zona Industrial", "resenna": "Instituto Autonomo de Policia del Estado Miranda.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.236000,-66.666000"},
                    {"nombre": "CICPC - Delegacion Municipal", "categoria": "Entes Publicos", "ubicacion": "Calle Sucre, Edificio CICPC", "resenna": "Delegacion del Cuerpo de Investigaciones Cientificas.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.237000,-66.667000"},
                    {"nombre": "Tribunales de Santa Teresa", "categoria": "Entes Publicos", "ubicacion": "Av. Romulo Gallegos, Palacio de Justicia", "resenna": "Sede de los Tribunales. Administracion de justicia.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.238000,-66.668000"},
                    {"nombre": "Hidrocapital - Oficina Comercial", "categoria": "Entes Publicos", "ubicacion": "Av. Bolivar, Centro Comercial Los Proceres", "resenna": "Oficina comercial de Hidrocapital. Atencion para tramites de agua.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.239000,-66.669000"},
                    {"nombre": "Unicasa", "categoria": "Comercio", "ubicacion": "Av. Intercomunal, Centro Comercial Santa Teresa Mall", "resenna": "Hipermercado con gran variedad de productos.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.240000,-66.670000"},
                    {"nombre": "Traki", "categoria": "Comercio", "ubicacion": "Av. Principal, Centro Comercial Las Americas", "resenna": "Tienda por departamentos.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.241000,-66.671000"},
                    {"nombre": "La Total", "categoria": "Comercio", "ubicacion": "Av. Bolivar, Centro Comercial El Paseo", "resenna": "Tienda de electrodomesticos y tecnologia.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.242000,-66.672000"},
                    {"nombre": "El Castillo", "categoria": "Comercio", "ubicacion": "Calle Bolivar, Local 5", "resenna": "Tienda de ropa, calzado y accesorios.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.243000,-66.673000"},
                    {"nombre": "El Palacio del Blumer", "categoria": "Comercio", "ubicacion": "Av. Bolivar, Local 15", "resenna": "Tienda especializada en blumer y lenceria.", "estrellas": 4, "maps_url": "https://maps.google.com/?q=10.244000,-66.674000"}
                ]
                
                for c in comercios_predeterminados:
                    s.execute(text("""
                        INSERT INTO comercios (nombre, categoria, ubicacion, resenna_willian, estrellas_w, maps_url, visitas)
                        VALUES (:n, :c, :u, :r, :e, :m, 0)
                    """), {
                        "n": c["nombre"],
                        "c": c["categoria"],
                        "u": c["ubicacion"],
                        "r": c["resenna"],
                        "e": c["estrellas"],
                        "m": c["maps_url"]
                    })
                s.commit()
    except Exception:
        pass

# --- CREACION DE TABLAS ---
try:
    with conn.session as s:
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS comercios (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255),
            categoria VARCHAR(100),
            ubicacion TEXT,
            foto_url TEXT,
            resenna_willian TEXT,
            estrellas_w INTEGER,
            maps_url TEXT,
            visitas INTEGER DEFAULT 0
        )
        """))
        
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS visitas INTEGER DEFAULT 0"))
        except Exception:
            pass
        
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS fotos_comercios (
            id SERIAL PRIMARY KEY,
            comercio_id INTEGER,
            foto_data TEXT
        )
        """))
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS opiniones (
            id SERIAL PRIMARY KEY,
            comercio_id INTEGER,
            usuario VARCHAR(100),
            comentario TEXT,
            estrellas_u INTEGER,
            fecha VARCHAR(50)
        )
        """))
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY,
            conteo INTEGER
        )
        """))
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS denuncias (
            id SERIAL PRIMARY KEY,
            denunciante VARCHAR(255),
            comercio_afectado VARCHAR(255),
            motivo TEXT,
            fecha VARCHAR(50),
            estatus VARCHAR(50) DEFAULT 'Pendiente'
        )
        """))
        s.execute(text("CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, logo_data TEXT)"))
        
        # Verificar si existe el registro de visitas, si no, crearlo con valor 1500
        res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
        if not res_v:
            s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 1500)"))
        s.commit()
        
except Exception as e:
    st.error(f"Error al crear las tablas: {str(e)}")
    st.stop()

# --- AGREGAR COMERCIOS PREDETERMINADOS ---
agregar_comercios_predeterminados()

# --- LOGICA DE VISITAS TOTALES (COMIENZA EN 1500 Y SUMA +1 CADA VEZ) ---
if 'visitado' not in st.session_state:
    try:
        with conn.session as s:
            s.execute(text("UPDATE visitas SET conteo = conteo + 1 WHERE id = 1"))
            s.commit()
        st.session_state.visitado = True
    except Exception:
        pass

try:
    res_visitas = conn.query("SELECT conteo FROM visitas WHERE id = 1", ttl=0)
    total_visitas = res_visitas.iloc[0,0] if not res_visitas.empty else 1500
except Exception:
    total_visitas = 1500

# --- FUNCION DE IMAGEN OPTIMIZADA ---
def imagen_a_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            if hasattr(uploaded_file, 'size') and uploaded_file.size > 5 * 1024 * 1024:
                st.error("La imagen es muy grande (maximo 5MB)")
                return None
            
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
            st.error(f"Error al procesar la imagen: {e}")
            return None
    return None

# --- FUNCION PARA OBTENER EFEMERIDES ---
def obtener_efemerides():
    hoy = datetime.now()
    dia = hoy.day
    mes = hoy.month
    
    efemerides_venezuela_especificas = {
        (1, 1): "Fundacion de la ciudad de El Tocuyo (1545)",
        (2, 1): "Nacimiento de Jose Antonio Paez (1790)",
        (6, 1): "Batalla de Maturin (1813)",
        (8, 1): "Nacimiento de Simon Rodriguez (1769)",
        (10, 1): "Creacion del estado Zulia (1864)",
        (13, 1): "Creacion del estado Anzoategui (1909)",
        (15, 1): "Dia del Maestro en Venezuela",
        (23, 1): "Caida de la dictadura de Marcos Perez Jimenez (1958)",
        (27, 1): "Nacimiento de Juan Crisostomo Falcon (1820)",
        (2, 2): "Dia de Nuestra Senora de la Candelaria",
        (4, 2): "Inicio de la Rebelion del 4F (1992)",
        (7, 2): "Nacimiento de Romulo Gallegos (1884)",
        (12, 2): "Batalla de La Victoria (1814) - Dia de la Juventud",
        (14, 2): "Nacimiento de Antonio Jose de Sucre (1795)",
        (10, 3): "Nacimiento de Jose Maria Vargas (1786)",
        (28, 3): "Nacimiento de Francisco de Miranda (1750)",
        (19, 4): "Declaracion de la Independencia (1810)",
        (27, 4): "Nacimiento de Simon Bolivar (1783)",
        (3, 5): "Creacion de la Bandera Nacional (1811)",
        (24, 6): "Batalla de Carabobo (1821)",
        (5, 7): "Firma del Acta de Independencia (1811)",
        (24, 7): "Natalicio de Simon Bolivar (1783)",
        (3, 8): "Nacimiento de Juan Vicente Gonzalez (1810)",
        (13, 9): "Batalla de la Casa Fuerte (1812)",
        (12, 10): "Dia de la Resistencia Indigena",
        (27, 11): "Aniversario del Colegio de Ingenieros de Venezuela",
        (17, 12): "Muere Simon Bolivar en Santa Marta (1830)",
        (25, 12): "Navidad en Venezuela"
    }
    
    efemerides_mundo_especificas = {
        (1, 1): "Año Nuevo. Primer dia del año en el calendario gregoriano",
        (6, 1): "Dia de Reyes. Los tres reyes magos visitan al niño Jesus",
        (15, 1): "Nacimiento de Martin Luther King Jr. (1929)",
        (20, 1): "Dia de Martin Luther King Jr. en Estados Unidos",
        (27, 1): "Dia Internacional de Conmemoracion del Holocausto",
        (28, 1): "Nacimiento de Jose Marti (1853)",
        (2, 2): "Dia Mundial de los Humedales",
        (4, 2): "Dia Mundial contra el Cancer",
        (11, 2): "Dia Internacional de la Mujer y la Nina en la Ciencia",
        (14, 2): "Dia de San Valentin - Dia del Amor y la Amistad",
        (8, 3): "Dia Internacional de la Mujer",
        (21, 3): "Dia Internacional de la Eliminacion de la Discriminacion Racial",
        (22, 3): "Dia Mundial del Agua",
        (7, 4): "Dia Mundial de la Salud",
        (22, 4): "Dia de la Tierra",
        (1, 5): "Dia Internacional del Trabajo",
        (3, 5): "Dia Mundial de la Libertad de Prensa",
        (8, 5): "Dia Mundial de la Cruz Roja",
        (15, 5): "Dia Internacional de la Familia",
        (21, 5): "Dia Mundial de la Diversidad Cultural",
        (31, 5): "Dia Mundial sin Tabaco",
        (5, 6): "Dia Mundial del Ambiente",
        (8, 6): "Dia Mundial de los Oceanos",
        (20, 6): "Dia Mundial del Refugiado",
        (21, 6): "Dia Internacional del Yoga",
        (11, 7): "Dia Mundial de la Poblacion",
        (18, 7): "Dia Internacional de Nelson Mandela",
        (28, 7): "Dia Mundial contra la Hepatitis",
        (30, 7): "Dia Internacional de la Amistad",
        (9, 8): "Dia Internacional de los Pueblos Indigenas",
        (12, 8): "Dia Internacional de la Juventud",
        (19, 8): "Dia Mundial de la Asistencia Humanitaria",
        (26, 9): "Dia Mundial de la Prevencion del Embarazo no Planificado",
        (24, 10): "Dia de las Naciones Unidas",
        (31, 10): "Halloween",
        (2, 11): "Dia de los Difuntos",
        (20, 11): "Dia de la Revolucion Mexicana",
        (25, 12): "Navidad",
        (31, 12): "Fin de Año"
    }
    
    efemeride_ve = efemerides_venezuela_especificas.get((dia, mes), "Hoy conmemoramos la historia y cultura de Venezuela")
    efemeride_mundo = efemerides_mundo_especificas.get((dia, mes), "Hoy celebramos la diversidad y unidad del mundo")
    
    efemerides_extra_ve = [
        "El Salto Angel es la cascada mas alta del mundo con 979 metros",
        "Venezuela tiene 43 parques nacionales que protegen ecosistemas unicos",
        "La Orquidea es la flor nacional de Venezuela desde 1951",
        "El Turpial es el ave nacional de Venezuela",
        "El Araguaney fue declarado arbol nacional en 1948",
        "La Arepa es considerada patrimonio cultural de Venezuela"
    ]
    
    efemerides_extra_mundo = [
        "La Gran Muralla China es la estructura mas larga construida por el hombre",
        "El Monte Everest es la montana mas alta del mundo con 8848 metros",
        "El Oceano Pacifico es el oceano mas grande del mundo",
        "El Desierto del Sahara es el desierto calido mas grande del mundo",
        "El Amazonas es el rio mas caudaloso del mundo",
        "El Vaticano es el pais mas pequeno del mundo"
    ]
    
    extra_ve = random.choice(efemerides_extra_ve)
    extra_mundo = random.choice(efemerides_extra_mundo)
    
    return efemeride_ve, efemeride_mundo, extra_ve, extra_mundo

# --- ESTILO VENEZUELA ---
st.markdown("""
<style>
#MainMenu {display: none;}
footer {display: none;}
.stDeployButton {display: none;}
header {display: none;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stDecoration"] {display: none;}
[data-testid="stStatusWidget"] {display: none;}
.stAppDeployButton {display: none;}

.stApp { background-color: #111827; color: #ffffff; }
p, span, label, .stMarkdown { color: #ffffff; font-weight: 500; }

[data-testid="stSidebar"] { background-color: #1f2937; border-right: 2px solid #ffcc00; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #ffffff; font-weight: bold; }

button[data-baseweb="tab"] p { color: #ffffff; font-size: 1.1em; font-weight: bold; }
button[aria-selected="true"] p { color: #ffcc00; }

.venezuela-header {
    text-align: center;
    padding-top: 60px;
    padding-bottom: 40px;
    padding-left: 10px;
    padding-right: 10px;
    background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
    border-radius: 25px;
    margin-bottom: 30px;
    box-shadow: 0px 10px 20px rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.1);
}

.logo-main-container {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
}

.logo-main-container img {
    mix-blend-mode: multiply;
    filter: contrast(120%) brightness(110%);
    background-color: transparent;
}

.logo-container {
    text-align: center;
    margin-bottom: 20px;
}

.logo-container img {
    mix-blend-mode: multiply;
    filter: contrast(110%) brightness(110%);
}

.stars-arc { color: white; font-size: 1.2em; letter-spacing: 5px; font-weight: bold; text-shadow: 2px 2px 4px #000; margin-top: -10px; }

.ven-share-card {
    background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    border: 2px solid #ffffff;
    box-shadow: 0px 5px 15px rgba(0,0,0,0.5);
    margin-bottom: 10px;
}
.ven-share-text { color: white; font-weight: bold; text-shadow: 2px 2px 4px #000; text-decoration: none; font-size: 1.1em; }

input, textarea, [data-baseweb="select"] { background-color: #ffffff; color: #000000; font-weight: bold; }

.stats-panel { background: rgba(31, 41, 55, 0.9); padding: 15px; border-radius: 20px; border: 2px solid #ffcc00; text-align: center; margin-bottom: 20px; }
.holiday-panel { background: linear-gradient(135deg, #0033a0, #001a50); padding: 15px; border-radius: 10px; border-left: 5px solid #ffcc00; margin-bottom: 20px; }
.efemerides-panel { background: linear-gradient(135deg, #1a3a5c, #0a1a3a); padding: 15px; border-radius: 10px; border-left: 5px solid #ffcc00; margin-bottom: 15px; }
.footer-willian { background: #000; padding: 30px; text-align: center; border-top: 4px solid #ffcc00; margin-top: 50px; }
.master-panel { background-color: #0033a0; border: 3px solid #ffcc00; padding: 20px; border-radius: 15px; }

.stExpander { border: 1px solid #ffcc00; background-color: #1f2937; }

.bronze-plaque {
    background: linear-gradient(145deg, #8c6a31, #5d431a);
    border: 5px solid #d4af37;
    padding: 50px 20px;
    border-radius: 15px;
    text-align: center;
    box-shadow: inset 2px 2px 8px rgba(255,255,255,0.3), 10px 10px 25px rgba(0,0,0,0.7);
    margin: 50px auto;
    max-width: 1000px;
    position: relative;
    overflow: hidden;
}
.bronze-text { color: #ffd700; font-family: 'Times New Roman', serif; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.9); }
.screw { position: absolute; width: 18px; height: 18px; background: radial-gradient(circle at 30% 30%, #999, #333); border-radius: 50%; box-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
.screw::after { content: ''; position: absolute; top: 50%; left: 10%; width: 80%; height: 2px; background: #111; transform: translateY(-50%) rotate(45deg); }
.screw-tl { top: 15px; left: 15px; } .screw-tr { top: 15px; right: 15px; } .screw-bl { bottom: 15px; left: 15px; } .screw-br { bottom: 15px; right: 15px; }

/* Estilos botones compartir */
.share-wa {
    background: linear-gradient(135deg, #25D366, #128C7E);
    padding: 10px;
    border-radius: 25px;
    text-align: center;
    margin-bottom: 10px;
}
.copy-area {
    display: flex;
    gap: 5px;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL ---
with st.sidebar:
    try:
        logo_res = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
        if not logo_res.empty and logo_res.iloc[0,0]:
            st.markdown(f'<div class="logo-container"><img src="{logo_res.iloc[0,0]}" style="width:220px;"></div>', unsafe_allow_html=True)
    except Exception:
        pass
    st.title("Venezuela Gestion")
    
    # ============================================
    # BOTONES DE COMPARTIR (AGREGADOS SIN BORRAR NADA)
    # ============================================
    st.markdown("---")
    st.markdown("### 📢 Compartir App")
    
    app_url = get_app_url()
    whatsapp_url = f"https://api.whatsapp.com/send?text=📱 *Guía Comercial de Santa Teresa*%0A%0AEncuentra comercios, servicios y promociones en tu ciudad.%0A%0A🔗 {app_url}%0A%0A¡Descubre todo lo que nuestra comunidad tiene para ofrecer!"
    
    st.markdown(f'''
    <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
        <div class="share-wa">
            <span style="color: white; font-weight: bold;">📲 Compartir por WhatsApp</span>
        </div>
    </a>
    ''', unsafe_allow_html=True)
    
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        st.text_input("", value=app_url, disabled=True, key="url_sidebar", label_visibility="collapsed")
    with col_c2:
        if st.button("📋", key="copy_sidebar", help="Copiar enlace"):
            copy_to_clipboard(app_url)
            st.success("¡Copiado!")
    
    st.markdown("---")
    
    # Enlace directo
    app_url_old = "https://williantuguiasantateresa.streamlit.app/"
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <a href="{app_url_old}" target="_blank" style="text-decoration: none;">
            <div style="background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%); 
                        padding: 10px; 
                        border-radius: 10px; 
                        border: 2px solid #ffffff;
                        color: white;
                        font-weight: bold;
                        text-align: center;">
                VER GUIA COMERCIAL
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Panel de administracion (requiere clave)
    with st.expander("Acceso Administrador"):
        clave_admin = st.text_input("Clave:", type="password", key="admin_key")
        if clave_admin == "Juan*316*":
            st.success("Acceso concedido")
            
            st.markdown("---")
            st.write("### Panel de Control")
            
            tab_admin1, tab_admin2, tab_admin3, tab_admin4, tab_admin5, tab_admin6 = st.tabs(["Denuncias", "Agregar", "Editar", "Opiniones", "Logo", "📸 Subir Fotos"])
            
            with tab_admin1:
                st.write("### Gestion de Denuncias")
                try:
                    den_df = conn.query("SELECT * FROM denuncias ORDER BY id DESC", ttl=0)
                    if not den_df.empty:
                        st.dataframe(den_df[['id','denunciante','comercio_afectado','motivo','fecha','estatus']], use_container_width=True)
                        st.markdown("**Cambiar estatus:**")
                        den_ids = den_df['id'].tolist()
                        sel_den_id = st.selectbox("ID de denuncia", den_ids, key="sel_den")
                        nuevo_estatus = st.selectbox("Nuevo estatus", ["Pendiente", "En revision", "Resuelta", "Descartada"], key="nuevo_est_den")
                        if st.button("Actualizar estatus", key="btn_den_upd"):
                            with conn.session as s:
                                s.execute(text("UPDATE denuncias SET estatus=:e WHERE id=:id"), {"e": nuevo_estatus, "id": int(sel_den_id)})
                                s.commit()
                            st.success("Actualizado")
                            st.rerun()
                        if st.button("Eliminar denuncia", key="btn_den_del"):
                            with conn.session as s:
                                s.execute(text("DELETE FROM denuncias WHERE id=:id"), {"id": int(sel_den_id)})
                                s.commit()
                            st.success("Eliminada")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                
                st.markdown("---")
                st.write("### Nueva Denuncia")
                with st.form("form_denuncia"):
                    den_nombre = st.text_input("Tu nombre")
                    den_comercio = st.text_input("Comercio afectado")
                    den_motivo = st.text_area("Motivo")
                    if st.form_submit_button("Enviar"):
                        if den_nombre.strip() and den_comercio.strip() and den_motivo.strip():
                            with conn.session as s:
                                s.execute(text("INSERT INTO denuncias (denunciante, comercio_afectado, motivo, fecha) VALUES (:d, :c, :m, :f)"),
                                          {"d": den_nombre.strip(), "c": den_comercio.strip(), "m": den_motivo.strip(), "f": datetime.now().strftime("%d/%m/%Y")})
                                s.commit()
                            st.success("Denuncia registrada")
                            st.rerun()
            
            with tab_admin2:
                st.write("### Agregar Comercio")
                with st.form("add_comercio"):
                    add_n = st.text_input("Nombre")
                    add_cat = st.selectbox("Categoria", CAT_LIST)
                    add_ub = st.text_input("Ubicacion")
                    add_maps = st.text_input("Google Maps URL")
                    add_res = st.text_area("Reseña")
                    add_est = st.slider("Calificacion", 1, 5, 5)
                    add_fotos = st.file_uploader("Imagenes", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                    if st.form_submit_button("Registrar"):
                        if add_n:
                            with conn.session as s:
                                p_img = imagen_a_base64(add_fotos[0]) if add_fotos else None
                                res_ins = s.execute(text("""
                                    INSERT INTO comercios (nombre, categoria, ubicacion, resenna_willian, estrellas_w, foto_url, maps_url, visitas) 
                                    VALUES (:n, :c, :u, :r, :e, :f, :m, 0) RETURNING id
                                """), {"n": add_n, "c": add_cat, "u": add_ub, "r": add_res, "e": add_est, "f": p_img, "m": add_maps})
                                new_id = res_ins.fetchone()[0]
                                if new_id and add_fotos and len(add_fotos) > 1:
                                    for extra in add_fotos[1:]:
                                        s.execute(text("INSERT INTO fotos_comercios (comercio_id, foto_data) VALUES (:cid, :fd)"),
                                                  {"cid": new_id, "fd": imagen_a_base64(extra)})
                                s.commit()
                            st.success("Comercio agregado")
                            st.rerun()
                        else:
                            st.error("Nombre requerido")
            
            # TAB EDICION Y ELIMINACION
            with tab_admin3:
                st.write("### ✏️ Editar Comercio")
                try:
                    comercios_list = conn.query("SELECT id, nombre, categoria FROM comercios ORDER BY nombre", ttl=0)
                    
                    if not comercios_list.empty:
                        comercio_nombres = comercios_list['nombre'].tolist()
                        
                        st.markdown("#### Selecciona el comercio a EDITAR")
                        sel_comercio_edit = st.selectbox(
                            "Comercio para editar", 
                            comercio_nombres, 
                            key="select_edit_comercio"
                        )
                        
                        target_edit = comercios_list[comercios_list['nombre'] == sel_comercio_edit].iloc[0]
                        datos_comercio = conn.query("SELECT * FROM comercios WHERE id = :id", params={"id": int(target_edit['id'])}, ttl=0)
                        
                        if not datos_comercio.empty:
                            row = datos_comercio.iloc[0]
                            with st.form(key="form_editar_comercio"):
                                st.markdown(f"**Editando: {row['nombre']}**")
                                new_n = st.text_input("Nombre", value=row['nombre'] if row['nombre'] else "")
                                new_cat = st.selectbox("Categoria", CAT_LIST, index=CAT_LIST.index(row['categoria']) if row['categoria'] in CAT_LIST else 0, key="edit_cat")
                                new_ub = st.text_input("Ubicacion", value=row['ubicacion'] if row['ubicacion'] else "")
                                new_maps = st.text_input("Google Maps URL", value=row['maps_url'] if row['maps_url'] else "")
                                new_est = st.slider("Calificacion", 1, 5, int(row['estrellas_w']) if row['estrellas_w'] else 3, key="edit_est")
                                new_res = st.text_area("Reseña", value=row['resenna_willian'] if row['resenna_willian'] else "")
                                if st.form_submit_button("💾 Guardar Cambios"):
                                    with conn.session as s:
                                        s.execute(text("UPDATE comercios SET nombre=:n, categoria=:c, ubicacion=:u, resenna_willian=:r, estrellas_w=:e, maps_url=:m WHERE id=:id"),
                                                  {"n": new_n, "c": new_cat, "u": new_ub, "r": new_res, "e": new_est, "m": new_maps, "id": int(row['id'])})
                                        s.commit()
                                    st.success(f"✅ Comercio '{new_n}' actualizado")
                                    st.rerun()
                        
                        st.markdown("---")
                        st.markdown("### 🗑️ Eliminar Comercio")
                        st.warning("⚠️ Esta accion es irreversible.")
                        sel_comercio_delete = st.selectbox("Selecciona el comercio a ELIMINAR", comercio_nombres, key="select_delete_comercio")
                        target_delete = comercios_list[comercios_list['nombre'] == sel_comercio_delete].iloc[0]
                        st.info(f"📌 Comercio seleccionado: **{target_delete['nombre']}**")
                        confirmar_texto = st.text_input(f"Escribe **ELIMINAR** para confirmar la eliminacion", key="confirm_delete_input")
                        if st.button("🗑️ ELIMINAR Comercio", type="secondary", key="btn_delete_comercio_final"):
                            if confirmar_texto == "ELIMINAR":
                                with conn.session as s:
                                    s.execute(text("DELETE FROM fotos_comercios WHERE comercio_id=:id"), {"id": int(target_delete['id'])})
                                    s.execute(text("DELETE FROM opiniones WHERE comercio_id=:id"), {"id": int(target_delete['id'])})
                                    s.execute(text("DELETE FROM comercios WHERE id=:id"), {"id": int(target_delete['id'])})
                                    s.commit()
                                st.success(f"✅ Comercio eliminado")
                                st.rerun()
                            else:
                                st.error("❌ No se elimino. Escribe exactamente 'ELIMINAR'")
                    else:
                        st.info("No hay comercios registrados")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            
            with tab_admin4:
                st.write("### Gestion de Opiniones")
                try:
                    op_all = conn.query("""
                        SELECT o.id, c.nombre AS comercio, o.usuario, o.comentario, o.estrellas_u, o.fecha
                        FROM opiniones o
                        LEFT JOIN comercios c ON o.comercio_id = c.id
                        ORDER BY o.id DESC
                    """, ttl=0)
                    if not op_all.empty:
                        st.dataframe(op_all, use_container_width=True)
                        op_ids = op_all['id'].tolist()
                        del_id = st.selectbox("ID a eliminar", op_ids)
                        if st.button("Eliminar Opinion"):
                            with conn.session as s:
                                s.execute(text("DELETE FROM opiniones WHERE id=:id"), {"id": int(del_id)})
                                s.commit()
                            st.success("Eliminada")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            
            with tab_admin5:
                st.write("### Configurar Logo")
                try:
                    logo_actual = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
                    if not logo_actual.empty and logo_actual.iloc[0,0]:
                        st.markdown(f'<img src="{logo_actual.iloc[0,0]}" style="width:150px;">', unsafe_allow_html=True)
                        if st.button("Eliminar Logo"):
                            with conn.session as s:
                                s.execute(text("UPDATE configuracion SET logo_data=NULL WHERE id=1"))
                                s.commit()
                            st.rerun()
                except Exception:
                    pass
                
                nuevo_logo = st.file_uploader("Subir Logo", type=["png", "jpg", "jpeg"])
                if nuevo_logo and st.button("Guardar Logo"):
                    logo_b64 = imagen_a_base64(nuevo_logo)
                    if logo_b64:
                        with conn.session as s:
                            existe = s.execute(text("SELECT id FROM configuracion WHERE id=1")).fetchone()
                            if existe:
                                s.execute(text("UPDATE configuracion SET logo_data=:l WHERE id=1"), {"l": logo_b64})
                            else:
                                s.execute(text("INSERT INTO configuracion (id, logo_data) VALUES (1, :l)"), {"l": logo_b64})
                            s.commit()
                        st.success("Logo guardado")
                        st.rerun()
            
            with tab_admin6:
                st.write("### 📸 Subir Fotos a Comercios")
                try:
                    comercios_lista = conn.query("SELECT id, nombre FROM comercios ORDER BY nombre", ttl=0)
                    if not comercios_lista.empty:
                        comercio_opciones = {row['nombre']: row['id'] for _, row in comercios_lista.iterrows()}
                        comercio_sel = st.selectbox("Selecciona el Comercio", list(comercio_opciones.keys()), key="select_comercio_fotos")
                        comercio_id = comercio_opciones[comercio_sel]
                        
                        fotos_existentes = conn.query("SELECT id, foto_data FROM fotos_comercios WHERE comercio_id = :cid", params={"cid": comercio_id}, ttl=0)
                        if not fotos_existentes.empty:
                            st.markdown("#### 📷 Fotos actuales:")
                            cols = st.columns(3)
                            for idx, (_, foto) in enumerate(fotos_existentes.iterrows()):
                                with cols[idx % 3]:
                                    st.image(foto['foto_data'], use_container_width=True)
                                    if st.button(f"🗑️ Eliminar", key=f"del_foto_{foto['id']}"):
                                        with conn.session as s:
                                            s.execute(text("DELETE FROM fotos_comercios WHERE id = :fid"), {"fid": foto['id']})
                                            s.commit()
                                        st.success("Foto eliminada")
                                        st.rerun()
                        
                        st.markdown("---")
                        fotos_subir = st.file_uploader("Seleccionar fotos", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="upload_fotos")
                        if fotos_subir and st.button("✅ Guardar Fotos", key="btn_guardar_fotos"):
                            fotos_guardadas = 0
                            for foto in fotos_subir:
                                foto_b64 = imagen_a_base64(foto)
                                if foto_b64:
                                    with conn.session as s:
                                        s.execute(text("INSERT INTO fotos_comercios (comercio_id, foto_data) VALUES (:cid, :foto)"),
                                                  {"cid": comercio_id, "foto": foto_b64})
                                        s.commit()
                                    fotos_guardadas += 1
                            if fotos_guardadas > 0:
                                st.success(f"✅ {fotos_guardadas} foto(s) guardada(s)")
                                st.rerun()
                    else:
                        st.info("No hay comercios registrados")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- ENCABEZADO PRINCIPAL ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★★★★★★★★</div></div>', unsafe_allow_html=True)

# --- LOGO CENTRADO ---
try:
    logo_res_main = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
    if not logo_res_main.empty and logo_res_main.iloc[0,0]:
        st.markdown(f'<div class="logo-main-container"><img src="{logo_res_main.iloc[0,0]}" style="width:350px;"></div>', unsafe_allow_html=True)
except Exception:
    pass

# --- LOGICA TEMPORAL Y EFEMERIDES ---
ahora_vzla = datetime.utcnow() - timedelta(hours=4)
dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

efemeride_ve, efemeride_mundo, extra_ve, extra_mundo = obtener_efemerides()

festivos_2026 = [
    (datetime(2026, 1, 1), "Año Nuevo"),
    (datetime(2026, 2, 16), "Lunes de Carnaval"),
    (datetime(2026, 2, 17), "Martes de Carnaval"),
    (datetime(2026, 3, 19), "Dia de San Jose"),
    (datetime(2026, 4, 2), "Jueves Santo"),
    (datetime(2026, 4, 3), "Viernes Santo"),
    (datetime(2026, 4, 19), "Declaracion de la Independencia"),
    (datetime(2026, 5, 1), "Dia del Trabajador"),
    (datetime(2026, 6, 24), "Batalla de Carabobo"),
    (datetime(2026, 7, 5), "Dia de la Independencia"),
    (datetime(2026, 7, 24), "Natalicio de Simon Bolivar"),
    (datetime(2026, 10, 12), "Dia de la Resistencia Indigena"),
    (datetime(2026, 12, 24), "Vispera de Navidad"),
    (datetime(2026, 12, 25), "Navidad"),
    (datetime(2026, 12, 31), "Fin de Año")
]

proximo_festivo = "No hay mas festivos este año"
for fecha, nombre in festivos_2026:
    if fecha.date() >= ahora_vzla.date():
        proximo_festivo = f"{nombre} ({fecha.strftime('%d/%m')})"
        break

st.markdown(f'''
<div class="stats-panel">
<span style="color:#ffcc00; font-size:1.1em; font-weight:bold;">{dias_semana[ahora_vzla.weekday()]}, {ahora_vzla.day} de {meses[ahora_vzla.month-1]} de {ahora_vzla.year}
</span><br>
<b style="color:#ffffff; font-size:1.4em;">{ahora_vzla.strftime("%I:%M %p")}</b><br>
<span style="font-size:1.2em; border-top: 1px solid #444; padding-top:5px; display:block; margin-top:5px; color:#ffffff;">🇻🇪 VISITAS TOTALES: {total_visitas}</span>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="efemerides-panel">
    <span style="color:#ffcc00; font-weight:bold; font-size:1.1em;">VENEZUELA</span><br>
    <span style="color:white;">📅 {efemeride_ve}</span><br>
    <span style="color:#ffcc00; font-size:0.9em; margin-top:5px; display:block;">✨ {extra_ve}</span>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="efemerides-panel">
    <span style="color:#ffcc00; font-weight:bold; font-size:1.1em;">MUNDO</span><br>
    <span style="color:white;">📅 {efemeride_mundo}</span><br>
    <span style="color:#ffcc00; font-size:0.9em; margin-top:5px; display:block;">✨ {extra_mundo}</span>
</div>
''', unsafe_allow_html=True)

st.markdown(f'''
<div class="holiday-panel">
    <span style="color:#ffcc00; font-weight:bold;">PROXIMO DIA FERIADO VENEZUELA 2026:</span><br>
    <span style="color:white; font-weight:bold;">{proximo_festivo}</span>
</div>
''', unsafe_allow_html=True)

# --- GUIA COMERCIAL ---
st.title("Guia Comercial Almenar")

# --- ENLACES ---
link_app = "https://williantuguiasantateresa.streamlit.app/"
whatsapp_url_principal = f"https://api.whatsapp.com/send?text=Mira la Guia Comercial de Santa Teresa! {link_app}"
col_s1, col_s2 = st.columns(2)
with col_s1:
    st.markdown(f'<a href="{whatsapp_url_principal}" target="_blank" style="text-decoration:none;"><div class="ven-share-card"><span class="ven-share-text">Compartir por WhatsApp</span></div></a>', unsafe_allow_html=True)
with col_s2:
    st.markdown(f'<div class="ven-share-card"><span class="ven-share-text">Enlace Directo:</span><br><b style="color:#ffcc00; font-size:0.9em;">{link_app}</b></div>', unsafe_allow_html=True)

st.markdown("---")
busq = st.text_input("Que buscas en Santa Teresa?", placeholder="Ej: Panaderia, Farmacia...")
tab_labels = ["Todos"] + CAT_LIST
tabs_main = st.tabs(tab_labels)

try:
    df = conn.query("SELECT * FROM comercios", ttl=0)
except Exception:
    df = pd.DataFrame()

try:
    todas_opiniones = conn.query("SELECT * FROM opiniones ORDER BY id DESC", ttl=0)
except Exception:
    todas_opiniones = pd.DataFrame()

try:
    todas_fotos = conn.query("SELECT * FROM fotos_comercios", ttl=0)
except Exception:
    todas_fotos = pd.DataFrame()

for i, tab in enumerate(tabs_main):
    with tab:
        categoria_seleccionada = tab_labels[i]
        if not df.empty:
            filtrado = df[df['nombre'].str.contains(busq, case=False) | df['categoria'].str.contains(busq, case=False)]
            if categoria_seleccionada != "Todos":
                filtrado = filtrado[filtrado['categoria'] == categoria_seleccionada]
            
            if filtrado.empty:
                st.warning(f"No hay comercios registrados en {categoria_seleccionada}." if categoria_seleccionada != "Todos" else "No se encontraron resultados.")
            else:
                for idx, r in filtrado.iterrows():
                    expander_titulo = f"{r['nombre']} - {r['categoria']}"
                    with st.expander(expander_titulo):
                        visit_key = f"visited_{r['id']}"
                        if visit_key not in st.session_state:
                            try:
                                with conn.session as s:
                                    s.execute(text("UPDATE comercios SET visitas = visitas + 1 WHERE id = :id"), {"id": int(r['id'])})
                                    s.commit()
                                st.session_state[visit_key] = True
                            except Exception:
                                pass

                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            if isinstance(r['foto_url'], str) and (r['foto_url'].startswith('http') or r['foto_url'].startswith('data:image')):
                                st.image(r['foto_url'], use_container_width=True, caption="Foto Principal")
                            
                            extras = todas_fotos[todas_fotos['comercio_id'] == r['id']]
                            if not extras.empty:
                                for _, f_row in extras.iterrows():
                                    try:
                                        st.image(f_row['foto_data'], use_container_width=True)
                                    except Exception:
                                        pass

                        with col_info:
                            st.write(f"**Ubicacion:** {r['ubicacion']}")
                            if r['maps_url']:
                                st.link_button("IR A ESTA UBICACION (Google Maps)", r['maps_url'], type="primary", use_container_width=True)
                            try:
                                estrellas_w_val = int(r['estrellas_w']) if r['estrellas_w'] is not None and str(r['estrellas_w']).isdigit() else 0
                                st.write(f"**Calificacion Willian:** {'*' * estrellas_w_val}")
                            except:
                                st.write(f"**Calificacion Willian:** ")
                            st.info(f"**Reseña de Willian:** {r['resenna_willian']}")
                            st.markdown("---")
                            if not todas_opiniones.empty:
                                op_df = todas_opiniones[todas_opiniones['comercio_id'] == r['id']]
                                for _, op in op_df.iterrows():
                                    try:
                                        estrellas_u_val = int(op['estrellas_u']) if op['estrellas_u'] is not None and str(op['estrellas_u']).isdigit() else 0
                                        st.markdown(f"<div style='border-bottom: 1px solid #444; padding: 5px;'><b>{op['usuario']}</b>: {op['comentario']} ({'*'*estrellas_u_val})</div>", unsafe_allow_html=True)
                                    except:
                                        st.markdown(f"<div style='border-bottom: 1px solid #444; padding: 5px;'><b>{op['usuario']}</b>: {op['comentario']}</div>", unsafe_allow_html=True)

                        st.markdown("##### Deja tu opinion")
                        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
                        form_key = f"opinion_form_{r['id']}_{idx}_{i}_{unique_id}"
                        with st.form(key=form_key):
                            op_usuario = st.text_input("Tu nombre", key=f"op_user_{r['id']}_{idx}_{i}_{unique_id}")
                            op_comentario = st.text_area("Comentario", key=f"op_com_{r['id']}_{idx}_{i}_{unique_id}")
                            op_estrellas = st.slider("Tu calificacion", 1, 5, 5, key=f"op_est_{r['id']}_{idx}_{i}_{unique_id}")
                            if st.form_submit_button("Enviar opinion"):
                                if op_usuario.strip() and op_comentario.strip():
                                    fecha_op = ahora_vzla.strftime("%d/%m/%Y")
                                    try:
                                        with conn.session as s:
                                            s.execute(text(
                                                "INSERT INTO opiniones (comercio_id, usuario, comentario, estrellas_u, fecha) "
                                                "VALUES (:cid, :u, :c, :e, :f)"
                                            ), {"cid": int(r['id']), "u": op_usuario.strip(), "c": op_comentario.strip(), "e": op_estrellas, "f": fecha_op})
                                            s.commit()
                                        st.success("Opinion enviada! Gracias.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error al guardar opinion: {e}")
                                else:
                                    st.warning("Escribe tu nombre y comentario antes de enviar.")

# --- PIE DE PAGINA ---
st.markdown("""
<div class='footer-willian'>
    <p style='color: #ffcc00 !important; font-size: 1.2em; font-weight: bold; margin-bottom: 10px;'>
        UNETE A NOSOTROS Y QUE TU NEGOCIO FORME PARTE DE ESTA GUIA COMERCIAL!
    </p>
    <p style='color: #ffffff !important; font-size: 1.1em;'>
        Contactanos por el 04242004015 (Solo WhatsApp)
    </p>
</div>
""", unsafe_allow_html=True)

# --- PLACA DE BRONCE ---
st.markdown("""
<div class="bronze-plaque">
    <div class="screw screw-tl"></div><div class="screw screw-tr"></div><div class="screw screw-bl"></div><div class="screw screw-br"></div>
    <div class="bronze-text">
        <span style="font-size: 2.2em;">Generado por Willian Almenar</span><br><br>
        <span style="font-size: 1.5em; opacity: 0.85;">Prohibida la reproduccion total o parcial</span><br>
        <span style="font-size: 1.8em; letter-spacing: 6px; display: block; margin: 15px 0;">DERECHOS RESERVADOS</span>
        <span style="font-size: 1.9em;">Santa Teresa del Tuy 2.026</span>
    </div>
</div>
""", unsafe_allow_html=True)
