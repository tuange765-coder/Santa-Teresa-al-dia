import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from sqlalchemy import text
from PIL import Image
import base64
import io
import requests
import os
import tempfile

# --- CONFIGURACION BASICA ---
st.set_page_config(page_title="Santa Teresa al Dia", page_icon="🇻🇪", layout="wide")

CARACAS_TZ = pytz.timezone('America/Caracas')

def get_fecha_hora_venezuela():
    return datetime.now(pytz.UTC).astimezone(CARACAS_TZ)

# --- CONEXION A BASE DE DATOS ---
def init_connection():
    try:
        if "DATABASE_URL" in st.secrets:
            conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
        else:
            st.error("No se encontro DATABASE_URL en secrets")
            st.stop()
        conn.query("SELECT 1", ttl=0)
        return conn
    except Exception as e:
        st.error(f"Error de conexion: {e}")
        st.stop()

conn = init_connection()

# --- CREAR TABLAS (UNA SOLA VEZ) ---
def crear_tablas():
    try:
        with conn.session as s:
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                categoria TEXT,
                contenido TEXT,
                fecha TEXT
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS negocios (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                categoria TEXT,
                resena TEXT,
                imagen TEXT,
                direccion TEXT
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS reflexiones (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                contenido TEXT,
                versiculo TEXT,
                fecha TEXT,
                activo BOOLEAN DEFAULT TRUE
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
                conteo INTEGER DEFAULT 0
            )
            """))
            
            s.execute(text("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                dolar REAL DEFAULT 65.0
            )
            """))
            
            res = s.execute(text("SELECT COUNT(*) FROM visitas WHERE id = 1")).fetchone()
            if res[0] == 0:
                s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
            
            res2 = s.execute(text("SELECT COUNT(*) FROM configuracion WHERE id = 1")).fetchone()
            if res2[0] == 0:
                s.execute(text("INSERT INTO configuracion (id, dolar) VALUES (1, 65.0)"))
            
            res3 = s.execute(text("SELECT COUNT(*) FROM noticias")).fetchone()
            if res3[0] == 0:
                fecha = datetime.now().strftime("%d/%m/%Y")
                s.execute(text("INSERT INTO noticias (titulo, categoria, contenido, fecha) VALUES ('Bienvenidos a Santa Teresa al Dia', 'Nacional', 'Un espacio para mantenernos informados.', :f)", {"f": fecha}))
                s.execute(text("INSERT INTO noticias (titulo, categoria, contenido, fecha) VALUES ('Cultura y Tradicion', 'Reportajes', 'Conoce nuestras tradiciones.', :f)", {"f": fecha}))
            
            res4 = s.execute(text("SELECT COUNT(*) FROM reflexiones")).fetchone()
            if res4[0] == 0:
                s.execute(text("INSERT INTO reflexiones (titulo, contenido, versiculo, fecha, activo) VALUES ('La Paz de Dios', 'No se angustien por nada.', 'Filipenses 4:6-7', '2026-01-01', TRUE)"))
            
            s.commit()
    except Exception as e:
        st.error(f"Error: {e}")

crear_tablas()

# --- DOLAR ---
def get_dolar():
    try:
        res = conn.query("SELECT dolar FROM configuracion WHERE id = 1", ttl=0)
        return res.iloc[0,0] if not res.empty else 65.0
    except:
        return 65.0

def actualizar_dolar():
    try:
        r = requests.get("https://ve.dolarapi.com/v1/dolares", timeout=3)
        if r.status_code == 200:
            for item in r.json():
                if item.get("nombre") == "BCV":
                    nuevo = float(item["precio"])
                    with conn.session as s:
                        s.execute(text("UPDATE configuracion SET dolar = :p WHERE id = 1"), {"p": nuevo})
                        s.commit()
                    return nuevo
    except:
        pass
    return None

# --- FUNCIONES GENERALES ---
def contar_visita():
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

def img_to_base64(file):
    if file:
        try:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((500, 500))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        except:
            return None
    return None

# --- NOTICIAS ---
def add_noticia(titulo, categoria, contenido):
    try:
        fecha = get_fecha_hora_venezuela().strftime("%d/%m/%Y")
        with conn.session as s:
            s.execute(text("INSERT INTO noticias (titulo, categoria, contenido, fecha) VALUES (:t, :c, :cont, :f)"),
                     {"t": titulo, "c": categoria, "cont": contenido, "f": fecha})
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
def add_negocio(nombre, categoria, resena, direccion, imagen):
    try:
        img = img_to_base64(imagen) if imagen else None
        with conn.session as s:
            s.execute(text("INSERT INTO negocios (nombre, categoria, resena, imagen, direccion) VALUES (:n, :c, :r, :i, :d)"),
                     {"n": nombre, "c": categoria, "r": resena, "i": img, "d": direccion})
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
        fecha = get_fecha_hora_venezuela().strftime("%d/%m/%Y")
        with conn.session as s:
            s.execute(text("UPDATE reflexiones SET activo = FALSE"))
            s.execute(text("INSERT INTO reflexiones (titulo, contenido, versiculo, fecha, activo) VALUES (:t, :c, :v, :f, TRUE)"),
                     {"t": titulo, "c": contenido, "v": versiculo, "f": fecha})
            s.commit()
        return True
    except:
        return False

def get_reflexion():
    try:
        df = conn.query("SELECT * FROM reflexiones WHERE activo = TRUE LIMIT 1", ttl=0)
        return df.iloc[0] if not df.empty else None
    except:
        return None

# --- DENUNCIAS ---
def add_denuncia(nombre, titulo, descripcion, ubicacion):
    try:
        fecha = get_fecha_hora_venezuela().strftime("%d/%m/%Y")
        with conn.session as s:
            s.execute(text("INSERT INTO denuncias (denunciante, titulo, descripcion, ubicacion, fecha, estatus) VALUES (:d, :t, :desc, :u, :f, 'Pendiente')"),
                     {"d": nombre or "Anonimo", "t": titulo, "desc": descripcion, "u": ubicacion, "f": fecha})
            s.commit()
        return True
    except:
        return False

def get_denuncias():
    try:
        return conn.query("SELECT * FROM denuncias ORDER BY id DESC", ttl=0)
    except:
        return pd.DataFrame()

# --- OPINIONES ---
def add_opinion(usuario, comentario, calificacion):
    try:
        fecha = get_fecha_hora_venezuela().strftime("%d/%m/%Y %H:%M")
        with conn.session as s:
            s.execute(text("INSERT INTO opiniones (usuario, comentario, calificacion, fecha, aprobada) VALUES (:u, :c, :cal, :f, FALSE)"),
                     {"u": usuario, "c": comentario, "cal": calificacion, "f": fecha})
            s.commit()
        return True
    except:
        return False

def get_opiniones(aprobadas=True):
    try:
        if aprobadas:
            return conn.query("SELECT * FROM opiniones WHERE aprobada = TRUE ORDER BY id DESC", ttl=0)
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

def delete_opinion(id_):
    try:
        with conn.session as s:
            s.execute(text("DELETE FROM opiniones WHERE id = :id"), {"id": id_})
            s.commit()
        return True
    except:
        return False

# --- ACTUALIZAR DOLAR ---
nuevo_dolar = actualizar_dolar()
dolar = get_dolar()

# --- CONTAR VISITA ---
if 'visitado' not in st.session_state:
    contar_visita()
    st.session_state.visitado = True

# --- ESTILOS ---
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #FFD700 0%, #00247D 50%, #CF142B 100%); }
.main > div { background-color: rgba(0,0,0,0.7); border-radius: 15px; padding: 20px; margin: 10px 0; }
[data-testid="stSidebar"] { background-color: rgba(0,0,0,0.85) !important; border-right: 3px solid #FFD700; }
[data-testid="stSidebar"] * { color: white !important; }
h1, h2, h3, h4 { color: #FFD700 !important; }
p, span, label { color: white !important; }
.stButton > button { background: linear-gradient(135deg, #FFD700, #CF142B); color: white !important; border: none; font-weight: bold; border-radius: 25px; }
input, textarea { background-color: rgba(255,255,255,0.95) !important; color: black !important; border-radius: 12px; border: 2px solid #FFD700 !important; }
.stats-panel { background: rgba(0,0,0,0.6); padding: 15px; border-radius: 20px; border: 2px solid #FFD700; text-align: center; margin-bottom: 20px; }
.bronze-footer { background: linear-gradient(145deg, #8c6a31, #5d431a); border: 5px solid #d4af37; padding: 25px; border-radius: 20px; text-align: center; margin-top: 50px; }
.bronze-footer p { color: #ffd700 !important; }
</style>
""", unsafe_allow_html=True)

# --- FECHA ---
ahora = get_fecha_hora_venezuela()
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
        "Portada", "Noticias", "Donde ir - Donde comprar", "Reflexiones",
        "Denuncias", "Opiniones"
    ])
    
    st.markdown("---")
    
    es_admin = False
    with st.expander("Administrador", expanded=False):
        clave = st.text_input("Clave:", type="password")
        if clave == "Juan*316*" or clave == "1966":
            es_admin = True
            st.success("Acceso concedido")
        elif clave:
            st.error("Clave incorrecta")

# --- PANEL SUPERIOR ---
visitas = get_visitas()

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

if menu == "Portada":
    st.title("Santa Teresa al Dia")
    
    st.markdown("### Ultimas Noticias")
    noticias = get_noticias()
    if not noticias.empty:
        for _, n in noticias.head(5).iterrows():
            st.info(f"**{n['titulo']}**\n\n{n['contenido'][:200]}...")
            st.caption(f"{n['fecha']} | {n['categoria']}")
            st.markdown("---")
    else:
        st.info("No hay noticias")
    
    st.markdown("---")
    st.markdown("### Reflexion del Dia")
    ref = get_reflexion()
    if ref is not None:
        st.markdown(f"**{ref['titulo']}**")
        st.write(ref['contenido'])
        st.caption(f"{ref['versiculo']}")

elif menu == "Noticias":
    st.title("Noticias")
    cat = st.selectbox("Filtrar", ["Todas", "Nacional", "Internacional", "Deportes", "Reportajes"])
    noticias = get_noticias()
    for _, n in noticias.iterrows():
        if cat == "Todas" or n['categoria'] == cat:
            st.markdown(f"### {n['titulo']}")
            st.caption(f"{n['fecha']} | {n['categoria']}")
            st.write(n['contenido'])
            st.markdown("---")

elif menu == "Donde ir - Donde comprar":
    st.title("Donde ir - Donde comprar")
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
                st.markdown(f"### {n['nombre']}")
                st.caption(n['categoria'])
                st.write(n['resena'])
                if n['direccion']:
                    st.write(f"📍 {n['direccion']}")
            st.markdown("---")
    else:
        st.info("No hay negocios agregados")

elif menu == "Reflexiones":
    st.title("Reflexiones")
    ref = get_reflexion()
    if ref is not None:
        st.markdown(f"### {ref['titulo']}")
        st.write(ref['contenido'])
        st.caption(f"{ref['versiculo']}")
    else:
        st.info("No hay reflexion activa")

elif menu == "Denuncias":
    st.title("Denuncias")
    tab1, tab2 = st.tabs(["Hacer Denuncia", "Ver Denuncias"])
    
    with tab1:
        with st.form("denuncia"):
            nombre = st.text_input("Tu nombre")
            titulo = st.text_input("Titulo")
            desc = st.text_area("Descripcion")
            ubic = st.text_input("Ubicacion")
            if st.form_submit_button("Enviar"):
                if titulo and desc:
                    add_denuncia(nombre, titulo, desc, ubic)
                    st.success("Denuncia enviada")
                    st.balloons()
    
    with tab2:
        for _, d in get_denuncias().iterrows():
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
                    add_opinion(usuario, comentario, calif)
                    st.success("Opinion enviada")
                    st.balloons()
    
    with tab2:
        for _, op in get_opiniones(aprobadas=True).iterrows():
            estrellas = "⭐" * op['calificacion']
            st.markdown(f"**{op['usuario']}** {estrellas}")
            st.write(op['comentario'])
            st.caption(op['fecha'])

# ============================================
# ADMINISTRACION (SOLO PARA TI)
# ============================================
if es_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Panel Admin")
    
    admin_menu = st.sidebar.radio("Gestionar", [
        "Noticias", "Negocios", "Reflexiones", "Denuncias", "Opiniones", "Config"
    ])
    
    if admin_menu == "Noticias":
        st.title("Gestionar Noticias")
        
        with st.form("nueva_noticia"):
            st.subheader("Publicar Noticia")
            titulo = st.text_input("Titulo")
            categoria = st.selectbox("Categoria", ["Nacional", "Internacional", "Deportes", "Reportajes"])
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("Publicar"):
                if titulo and contenido:
                    add_noticia(titulo, categoria, contenido)
                    st.success("Noticia publicada!")
                    st.rerun()
        
        st.markdown("---")
        st.subheader("Noticias Existentes")
        for _, n in get_noticias().iterrows():
            with st.expander(f"{n['titulo']}"):
                st.write(n['contenido'])
                if st.button("Eliminar", key=f"del_{n['id']}"):
                    delete_noticia(n['id'])
                    st.rerun()
    
    elif admin_menu == "Negocios":
        st.title("Gestionar Negocios")
        
        with st.form("nuevo_negocio"):
            st.subheader("Agregar Negocio")
            nombre = st.text_input("Nombre")
            categoria = st.text_input("Categoria")
            resena = st.text_area("Reseña")
            direccion = st.text_input("Direccion")
            imagen = st.file_uploader("Foto", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("Agregar"):
                if nombre and resena:
                    add_negocio(nombre, categoria, resena, direccion, imagen)
                    st.success("Negocio agregado!")
                    st.rerun()
        
        st.markdown("---")
        st.subheader("Negocios Existentes")
        for _, n in get_negocios().iterrows():
            with st.expander(f"{n['nombre']}"):
                if n['imagen']:
                    st.image(n['imagen'], width=200)
                st.write(n['resena'])
                if st.button("Eliminar", key=f"del_neg_{n['id']}"):
                    delete_negocio(n['id'])
                    st.rerun()
    
    elif admin_menu == "Reflexiones":
        st.title("Gestionar Reflexiones")
        
        with st.form("nueva_reflexion"):
            st.subheader("Nueva Reflexion")
            titulo = st.text_input("Titulo")
            versiculo = st.text_input("Versiculo")
            contenido = st.text_area("Contenido", height=150)
            if st.form_submit_button("Guardar"):
                if titulo and contenido:
                    add_reflexion(titulo, contenido, versiculo)
                    st.success("Reflexion guardada!")
                    st.rerun()
    
    elif admin_menu == "Denuncias":
        st.title("Gestionar Denuncias")
        for _, d in get_denuncias().iterrows():
            with st.expander(f"{d['titulo']}"):
                st.write(f"Denunciante: {d['denunciante']}")
                st.write(f"Descripcion: {d['descripcion']}")
                nuevo = st.selectbox("Estado", ["Pendiente", "En revision", "Resuelta"], key=f"est_{d['id']}")
                if st.button("Actualizar", key=f"upd_{d['id']}"):
                    with conn.session as s:
                        s.execute(text("UPDATE denuncias SET estatus = :e WHERE id = :id"), {"e": nuevo, "id": d['id']})
                        s.commit()
                    st.rerun()
    
    elif admin_menu == "Opiniones":
        st.title("Gestionar Opiniones")
        st.subheader("Pendientes de Aprobar")
        for _, op in get_opiniones(aprobadas=False).iterrows():
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
                            delete_opinion(op['id'])
                            st.rerun()
    
    elif admin_menu == "Config":
        st.title("Configuracion")
        st.write(f"Dolar actual: {dolar:.2f} Bs")
        if st.button("Actualizar Dolar manualmente"):
            nuevo = actualizar_dolar()
            if nuevo:
                st.success(f"Dolar actualizado a {nuevo:.2f} Bs")
                st.rerun()
            else:
                st.error("No se pudo obtener el dolar")

# --- FOOTER ---
st.markdown("""
<div class="bronze-footer">
    <p>⚜️ DESARROLLADO POR WILLIAN ALMENAR ⚜️</p>
    <p>Prohibida la reproduccion total o parcial - Derechos Reservados</p>
    <p>Santa Teresa del Tuy, 2026</p>
</div>
""", unsafe_allow_html=True)
