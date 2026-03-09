"""
Configuración central del sistema RPA.
Modificar estas variables según el entorno local.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Rutas ---
BASE_DIR = os.path.dirname(__file__)
PDF_CICLOS_DIR = os.path.join(BASE_DIR, "PDF_Ciclos")

# Directorio base de descargas (disco E:)
DIRECTORIO_DESCARGAS = "E:\\RPA_Descargas"

# --- Chrome ---
# Perfil "Diseñador" = Profile 4
CHROME_USER_DATA_DIR = r"C:\Users\Master PC\AppData\Local\Google\Chrome\User Data"
CHROME_PROFILE = "Profile 4"

# --- Plataforma educativa UPC ---
PLATAFORMA_URL = "https://aulavirtual.upc.edu.pe"

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"  # Modelo económico para minimizar costos

# --- Base de datos ---
DB_PATH = os.path.join(BASE_DIR, "registro.db")

# --- Tiempos de espera (ms) ---
TIMEOUT_NAVEGACION = 30_000
TIMEOUT_DESCARGA = 120_000

# --- Extensiones multimedia a buscar ---
EXTENSIONES_MULTIMEDIA = {".mp4", ".mp3", ".webm", ".m3u8", ".pdf", ".pptx", ".docx", ".xlsx", ".zip"}

# --- Cursos a excluir (no son cursos descargables) ---
CURSOS_EXCLUIR = {
    "INDUCCION",
    "MISION ACADEMICA EN DESALES UNIVERSITY, USA",
    "MISION ACADEMICA A LA UNIVERSIDAD SANTO TOMAS",
    "MISION ACADEMICA EN LA UNIVERSIDAD POLITECNICA DE CATALUÑA, ESPAÑA",
    "MISIÓN ACADÉMICA EN LA UNIVERSIDAD DE SANTO TOMAS, COLOMBIA",
    "TOPICOS EN GESTION DE SALUD 3",
}
