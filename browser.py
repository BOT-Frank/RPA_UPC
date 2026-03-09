"""
Módulo de gestión del navegador.
Copia el perfil de Chrome a una carpeta temporal para evitar conflictos
con instancias abiertas de Chrome, preservando cookies y sesión.
"""
import os
import shutil
import tempfile
from playwright.sync_api import sync_playwright
import config

# Carpeta temporal donde se copia el perfil (se reutiliza entre ejecuciones)
_TEMP_PROFILE_DIR = os.path.join(tempfile.gettempdir(), "rpa_upc_chrome_profile")


def abrir_navegador() -> tuple:
    """
    Copia el perfil de Chrome y lanza el navegador.
    Retorna (playwright, context, page).

    Se copia el perfil a una carpeta temporal para que:
    - No entre en conflicto si Chrome está abierto
    - Se preserven cookies y sesión del perfil original
    """
    # Ruta al perfil original
    perfil_origen = os.path.join(config.CHROME_USER_DATA_DIR, config.CHROME_PROFILE)

    if not os.path.isdir(perfil_origen):
        raise FileNotFoundError(
            f"No se encontró el perfil de Chrome: {perfil_origen}\n"
            f"Verifica CHROME_USER_DATA_DIR y CHROME_PROFILE en config.py"
        )

    # Copiar perfil a carpeta temporal
    print(f"[BROWSER] Copiando perfil '{config.CHROME_PROFILE}' a carpeta temporal...")
    _copiar_perfil(perfil_origen, _TEMP_PROFILE_DIR)

    # Lanzar Chrome con el perfil copiado
    pw = sync_playwright().start()

    try:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=_TEMP_PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            viewport={"width": 1366, "height": 768},
            timeout=60_000,  # 60s para el primer arranque
            ignore_default_args=["--enable-automation"],
        )
    except Exception as e:
        pw.stop()
        raise RuntimeError(
            f"No se pudo abrir Chrome: {e}\n"
            f"Si el problema persiste, elimina la carpeta temporal:\n"
            f"  {_TEMP_PROFILE_DIR}"
        )

    page = context.pages[0] if context.pages else context.new_page()

    print("[BROWSER] Chrome abierto con copia del perfil 'Diseñador'.")
    return pw, context, page


def cerrar_navegador(pw, context) -> None:
    """Cierra el contexto y Playwright de forma limpia."""
    try:
        context.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass
    print("[BROWSER] Navegador cerrado.")


def _copiar_perfil(origen: str, destino: str) -> None:
    """
    Copia los archivos esenciales del perfil de Chrome.
    No copia todo (sería muy lento), solo lo necesario para mantener sesión.
    """
    # Archivos clave para preservar la sesión
    archivos_esenciales = [
        "Cookies",
        "Cookies-journal",
        "Login Data",
        "Login Data-journal",
        "Web Data",
        "Web Data-journal",
        "Preferences",
        "Secure Preferences",
        "Local State",
        "Network",
        "Sessions",
        "Local Storage",
        "Session Storage",
        "IndexedDB",
    ]

    os.makedirs(destino, exist_ok=True)

    # Copiar Local State del directorio padre (User Data)
    local_state_src = os.path.join(config.CHROME_USER_DATA_DIR, "Local State")
    local_state_dst = os.path.join(destino, "Local State")
    if os.path.exists(local_state_src) and not os.path.exists(local_state_dst):
        shutil.copy2(local_state_src, local_state_dst)

    # Subdirectorio Default dentro del temporal (Playwright usa "Default" internamente)
    destino_default = os.path.join(destino, "Default")
    os.makedirs(destino_default, exist_ok=True)

    for nombre in archivos_esenciales:
        src = os.path.join(origen, nombre)
        dst = os.path.join(destino_default, nombre)

        if not os.path.exists(src):
            continue

        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        except (PermissionError, OSError) as e:
            # Algunos archivos pueden estar bloqueados, no es crítico
            print(f"  [WARN] No se pudo copiar {nombre}: {e}")

    print(f"[BROWSER] Perfil copiado a: {destino}")
