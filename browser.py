"""
Módulo de gestión del navegador.
Abre Chrome usando el perfil existente del usuario (con sesión ya iniciada)
para evitar tener que autenticarse manualmente.
"""
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
import config


def abrir_navegador() -> tuple:
    """
    Lanza Chrome con el perfil real del usuario.
    Retorna (playwright, browser, context, page) para que el llamador
    pueda cerrar los recursos al finalizar.
    """
    pw = sync_playwright().start()

    # launch_persistent_context usa el directorio de datos del usuario,
    # lo que preserva cookies, sesiones y extensiones.
    context = pw.chromium.launch_persistent_context(
        user_data_dir=config.CHROME_USER_DATA_DIR,
        channel="chrome",
        headless=False,  # visible para supervisión manual
        args=[
            f"--profile-directory={config.CHROME_PROFILE}",
            "--disable-blink-features=AutomationControlled",
        ],
        viewport={"width": 1280, "height": 800},
        timeout=config.TIMEOUT_NAVEGACION,
    )

    # Usar la primera pestaña si existe, o crear una nueva
    page = context.pages[0] if context.pages else context.new_page()

    print("[BROWSER] Chrome abierto con perfil de usuario existente.")
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
