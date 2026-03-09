"""
Configuración central del sistema RPA.
Modificar estas variables según el entorno local.
"""
import os

# --- Rutas ---
# Ruta al PDF con los nombres de los cursos
PDF_CURSOS = os.path.join(os.path.dirname(__file__), "cursos.pdf")

# Directorio base de descargas (disco E:)
# En Linux/Mac cambiar a una ruta válida, ej: "/mnt/e/RPA_Descargas"
DIRECTORIO_DESCARGAS = "E:\\RPA_Descargas"

# --- Chrome ---
# Ruta al perfil de Chrome con sesión iniciada.
# Windows típico: C:\Users\<usuario>\AppData\Local\Google\Chrome\User Data
# El canal "chrome" usa la instalación del sistema.
CHROME_USER_DATA_DIR = os.path.expanduser(
    os.path.join("~", "AppData", "Local", "Google", "Chrome", "User Data")
)
CHROME_PROFILE = "Default"  # o "Profile 1", etc.

# --- Plataforma educativa ---
# URL base de la plataforma (ajustar según corresponda)
PLATAFORMA_URL = "https://aulavirtual.upc.edu.pe"
# URL de búsqueda de cursos (placeholder — ajustar al DOM real)
BUSQUEDA_URL = f"{PLATAFORMA_URL}/course/search.php"

# --- Base de datos ---
DB_PATH = os.path.join(os.path.dirname(__file__), "registro.db")

# --- Tiempos de espera (ms) ---
TIMEOUT_NAVEGACION = 30_000
TIMEOUT_DESCARGA = 120_000

# --- Extensiones multimedia a buscar ---
EXTENSIONES_MULTIMEDIA = {".mp4", ".mp3", ".webm", ".m3u8", ".pdf", ".pptx", ".docx"}
