"""
=======================================================
  RPA_UPC — Modo Enseñanza (Teach Mode)
=======================================================

Abre el navegador y te guía paso a paso para enseñarle al bot
cómo navegar la plataforma. Graba cada paso como una "receta"
que luego se usa automáticamente.

Uso:
    python teach.py

Flujo:
    1. Abre Chrome con perfil Diseñador
    2. Navega a aulavirtual.upc.edu.pe/ultra/institution-page
    3. Te muestra la página actual y te pregunta qué hacer
    4. Tú le indicas paso a paso: dónde buscar cursos, dónde están
       las grabaciones, qué botones clickear
    5. Guarda todo en recipe.json para uso automático
"""
import json
import os
import sys
from datetime import datetime
from browser import abrir_navegador, cerrar_navegador
import config

RECIPE_PATH = os.path.join(os.path.dirname(__file__), "recipe.json")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


def main():
    print("\n" + "=" * 60)
    print("  RPA_UPC — MODO ENSEÑANZA")
    print("  Voy a abrir el navegador. Tú me guías paso a paso.")
    print("=" * 60)
    print()
    print("Comandos disponibles:")
    print("  screenshot     → Toma captura de la página actual")
    print("  click TEXTO    → Hace click en el elemento con ese texto")
    print("  clicksel CSS   → Hace click en un selector CSS")
    print("  url URL        → Navega a una URL")
    print("  scroll         → Baja la página")
    print("  esperar N      → Espera N segundos")
    print("  listar         → Lista todos los enlaces visibles")
    print("  listar-btn     → Lista todos los botones visibles")
    print("  guardar NOMBRE → Guarda este paso en la receta")
    print("  receta         → Muestra la receta actual")
    print("  info           → Muestra URL y título actual")
    print("  html           → Muestra HTML resumido de la página")
    print("  salir          → Guarda receta y cierra")
    print()

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # Cargar receta existente si hay
    receta = _cargar_receta()

    # Abrir navegador
    try:
        pw, context, page = abrir_navegador()
    except Exception as e:
        print(f"[ERROR] No se pudo abrir el navegador: {e}")
        print("  → Cierra TODAS las ventanas de Chrome e intenta de nuevo.")
        sys.exit(1)

    # Navegar a la página principal
    print("\n[NAV] Navegando a la plataforma...")
    try:
        page.goto("https://aulavirtual.upc.edu.pe/ultra/institution-page",
                   timeout=config.TIMEOUT_NAVEGACION)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"[ERROR] No se pudo acceder: {e}")

    _mostrar_info(page)

    # Loop interactivo
    try:
        while True:
            print()
            cmd = input("🎯 ¿Qué hago? > ").strip()
            if not cmd:
                continue

            partes = cmd.split(" ", 1)
            accion = partes[0].lower()
            argumento = partes[1] if len(partes) > 1 else ""

            try:
                if accion == "salir" or accion == "exit":
                    break

                elif accion == "screenshot" or accion == "ss":
                    ruta = _screenshot(page)
                    print(f"  Captura guardada: {ruta}")

                elif accion == "info":
                    _mostrar_info(page)

                elif accion == "click":
                    if not argumento:
                        print("  Uso: click TEXTO_DEL_ENLACE")
                        continue
                    _hacer_click_texto(page, argumento)

                elif accion == "clicksel":
                    if not argumento:
                        print("  Uso: clicksel SELECTOR_CSS")
                        continue
                    _hacer_click_selector(page, argumento)

                elif accion == "url":
                    if not argumento:
                        print("  Uso: url https://...")
                        continue
                    page.goto(argumento, timeout=config.TIMEOUT_NAVEGACION)
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(2000)
                    _mostrar_info(page)

                elif accion == "scroll":
                    page.evaluate("window.scrollBy(0, 500)")
                    print("  Scrolled down 500px")

                elif accion == "esperar":
                    segs = int(argumento) if argumento else 3
                    page.wait_for_timeout(segs * 1000)
                    print(f"  Esperé {segs} segundos")

                elif accion == "listar":
                    _listar_enlaces(page)

                elif accion == "listar-btn":
                    _listar_botones(page)

                elif accion == "html":
                    _mostrar_html_resumido(page)

                elif accion == "guardar":
                    if not argumento:
                        print("  Uso: guardar NOMBRE_DEL_PASO")
                        print("  Ejemplo: guardar buscar_curso")
                        continue
                    paso = _crear_paso(page, argumento)
                    receta["pasos"].append(paso)
                    print(f"  Paso guardado: '{argumento}'")
                    print(f"  URL: {paso['url']}")
                    print(f"  Total pasos en receta: {len(receta['pasos'])}")

                elif accion == "receta":
                    _mostrar_receta(receta)

                elif accion == "selector":
                    # Ayuda para encontrar selectores
                    if not argumento:
                        print("  Uso: selector TEXTO_PARCIAL")
                        continue
                    _buscar_selector(page, argumento)

                else:
                    print(f"  Comando no reconocido: '{accion}'")
                    print("  Escribe 'salir' para terminar")

            except Exception as e:
                print(f"  [ERROR] {e}")

    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")

    finally:
        # Guardar receta
        _guardar_receta(receta)
        print(f"\n[RECETA] Guardada en: {RECIPE_PATH}")
        print(f"  Total pasos: {len(receta['pasos'])}")

        # Cerrar navegador
        cerrar_navegador(pw, context)


def _mostrar_info(page):
    """Muestra URL y título de la página actual."""
    print(f"\n  📍 URL:    {page.url}")
    try:
        titulo = page.title()
        print(f"  📄 Título: {titulo}")
    except Exception:
        pass


def _screenshot(page) -> str:
    """Toma una captura de pantalla."""
    timestamp = datetime.now().strftime("%H%M%S")
    ruta = os.path.join(SCREENSHOTS_DIR, f"step_{timestamp}.png")
    page.screenshot(path=ruta, full_page=False)
    return ruta


def _hacer_click_texto(page, texto: str):
    """Hace click en un elemento que contiene el texto dado."""
    # Intentar varias estrategias
    selectores = [
        f"a:has-text('{texto}')",
        f"button:has-text('{texto}')",
        f"span:has-text('{texto}')",
        f"div[role='button']:has-text('{texto}')",
        f"li:has-text('{texto}')",
        f":has-text('{texto}')",
    ]

    for sel in selectores:
        try:
            elem = page.locator(sel).first
            if elem.is_visible(timeout=2000):
                elem.click()
                page.wait_for_timeout(2000)
                print(f"  Click exitoso en: '{texto}' (selector: {sel})")
                _mostrar_info(page)
                return
        except Exception:
            continue

    print(f"  No encontré elemento con texto: '{texto}'")
    print("  Prueba con 'listar' para ver los enlaces disponibles")


def _hacer_click_selector(page, selector: str):
    """Hace click en un selector CSS específico."""
    elem = page.locator(selector).first
    elem.click(timeout=5000)
    page.wait_for_timeout(2000)
    print(f"  Click exitoso en selector: {selector}")
    _mostrar_info(page)


def _listar_enlaces(page):
    """Lista todos los enlaces visibles en la página."""
    try:
        enlaces = page.locator("a:visible").all()
        print(f"\n  Enlaces visibles ({len(enlaces)}):")
        for i, link in enumerate(enlaces[:50]):
            try:
                texto = (link.text_content() or "").strip()[:60]
                href = (link.get_attribute("href") or "")[:80]
                if texto or href:
                    print(f"  {i+1:3}. [{texto}] → {href}")
            except Exception:
                continue
        if len(enlaces) > 50:
            print(f"  ... y {len(enlaces) - 50} más")
    except Exception as e:
        print(f"  Error listando enlaces: {e}")


def _listar_botones(page):
    """Lista todos los botones visibles."""
    try:
        botones = page.locator("button:visible, [role='button']:visible").all()
        print(f"\n  Botones visibles ({len(botones)}):")
        for i, btn in enumerate(botones[:30]):
            try:
                texto = (btn.text_content() or "").strip()[:60]
                clase = (btn.get_attribute("class") or "")[:40]
                if texto:
                    print(f"  {i+1:3}. [{texto}] clase: {clase}")
            except Exception:
                continue
    except Exception as e:
        print(f"  Error listando botones: {e}")


def _mostrar_html_resumido(page):
    """Muestra los elementos principales del DOM."""
    try:
        # Mostrar estructura de alto nivel
        resumen = page.evaluate("""() => {
            const items = [];
            // Buscar contenedores principales
            document.querySelectorAll('main, [role="main"], .content, #content, nav, [role="navigation"]').forEach(el => {
                items.push({
                    tag: el.tagName,
                    id: el.id,
                    class: el.className.toString().substring(0, 60),
                    children: el.children.length
                });
            });
            // Buscar inputs
            document.querySelectorAll('input:not([type="hidden"])').forEach(el => {
                items.push({
                    tag: 'INPUT',
                    type: el.type,
                    placeholder: el.placeholder,
                    name: el.name,
                    id: el.id
                });
            });
            return items.slice(0, 30);
        }""")
        print("\n  Estructura de la página:")
        for item in resumen:
            print(f"  • {item}")
    except Exception as e:
        print(f"  Error: {e}")


def _buscar_selector(page, texto: str):
    """Busca selectores que contengan un texto parcial."""
    try:
        resultados = page.evaluate(f"""() => {{
            const results = [];
            document.querySelectorAll('*').forEach(el => {{
                const t = el.textContent || '';
                if (t.toLowerCase().includes('{texto.lower()}') && t.length < 200) {{
                    results.push({{
                        tag: el.tagName,
                        id: el.id,
                        class: el.className.toString().substring(0, 50),
                        text: t.trim().substring(0, 80)
                    }});
                }}
            }});
            return results.slice(0, 20);
        }}""")
        print(f"\n  Elementos que contienen '{texto}':")
        for r in resultados:
            print(f"  • <{r['tag']}> id='{r['id']}' class='{r['class']}'")
            print(f"    texto: {r['text']}")
    except Exception as e:
        print(f"  Error: {e}")


def _crear_paso(page, nombre: str) -> dict:
    """Crea un paso de la receta con la información actual."""
    ruta_screenshot = _screenshot(page)
    return {
        "nombre": nombre,
        "url": page.url,
        "titulo": page.title(),
        "timestamp": datetime.now().isoformat(),
        "screenshot": ruta_screenshot,
        "notas": input("  Nota sobre este paso (Enter para omitir): ").strip(),
    }


def _cargar_receta() -> dict:
    """Carga la receta existente o crea una nueva."""
    if os.path.exists(RECIPE_PATH):
        try:
            with open(RECIPE_PATH, "r", encoding="utf-8") as f:
                receta = json.load(f)
            print(f"[RECETA] Cargada receta existente con {len(receta.get('pasos', []))} pasos")
            return receta
        except Exception:
            pass

    return {
        "plataforma": "aulavirtual.upc.edu.pe",
        "creada": datetime.now().isoformat(),
        "pasos": [],
    }


def _guardar_receta(receta: dict):
    """Guarda la receta en disco."""
    receta["actualizada"] = datetime.now().isoformat()
    with open(RECIPE_PATH, "w", encoding="utf-8") as f:
        json.dump(receta, f, ensure_ascii=False, indent=2)


def _mostrar_receta(receta: dict):
    """Muestra la receta actual."""
    pasos = receta.get("pasos", [])
    if not pasos:
        print("\n  La receta está vacía. Usa 'guardar NOMBRE' para agregar pasos.")
        return

    print(f"\n  Receta de navegación ({len(pasos)} pasos):")
    for i, paso in enumerate(pasos, 1):
        print(f"  {i}. [{paso['nombre']}]")
        print(f"     URL: {paso['url']}")
        if paso.get("notas"):
            print(f"     Nota: {paso['notas']}")


if __name__ == "__main__":
    main()
