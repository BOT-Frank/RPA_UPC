"""
=======================================================
  RPA_UPC — Modo Enseñanza (Teach Mode)
=======================================================

Abre el navegador y te permite guiarlo paso a paso desde la terminal.
Tú le dices a dónde ir, qué clickear, y él graba los pasos.

Uso:
    python teach.py
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
    _mostrar_ayuda()

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    receta = _cargar_receta()

    # Abrir navegador
    print("\n[BROWSER] Abriendo Chrome con perfil Diseñador...")
    print("  (Esto puede tomar unos segundos la primera vez)\n")
    try:
        pw, context, page = abrir_navegador()
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # NO navegar automáticamente — el usuario decide a dónde ir
    print("\n  Chrome está abierto. Escribe 'url' seguido de la dirección para navegar.")
    print("  Ejemplo: url https://aulavirtual.upc.edu.pe/ultra/institution-page\n")

    # Loop interactivo
    try:
        while True:
            cmd = input(">>> ").strip()
            if not cmd:
                continue

            partes = cmd.split(" ", 1)
            accion = partes[0].lower()
            argumento = partes[1].strip() if len(partes) > 1 else ""

            try:
                if accion in ("salir", "exit", "q"):
                    break

                elif accion == "ayuda" or accion == "help" or accion == "h":
                    _mostrar_ayuda()

                elif accion in ("screenshot", "ss"):
                    ruta = _screenshot(page)
                    print(f"  Captura: {ruta}")

                elif accion == "info" or accion == "i":
                    _mostrar_info(page)

                elif accion == "url":
                    if not argumento:
                        print("  Uso: url https://aulavirtual.upc.edu.pe/ultra/institution-page")
                        continue
                    print(f"  Navegando a: {argumento}")
                    page.goto(argumento, timeout=60_000)
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(3000)
                    _mostrar_info(page)

                elif accion == "click":
                    if not argumento:
                        print("  Uso: click TEXTO_DEL_ENLACE")
                        continue
                    _hacer_click_texto(page, argumento)

                elif accion == "clickn":
                    # Click por número de la lista
                    if not argumento:
                        print("  Uso: clickn NUMERO (del resultado de 'listar')")
                        continue
                    _hacer_click_numero(page, int(argumento))

                elif accion == "clicksel":
                    if not argumento:
                        print("  Uso: clicksel SELECTOR_CSS")
                        continue
                    _hacer_click_selector(page, argumento)

                elif accion in ("listar", "ls"):
                    _listar_enlaces(page)

                elif accion in ("listar-btn", "btn"):
                    _listar_botones(page)

                elif accion == "scroll":
                    cant = int(argumento) if argumento else 500
                    page.evaluate(f"window.scrollBy(0, {cant})")
                    print(f"  Scroll {cant}px")

                elif accion == "scrollup":
                    cant = int(argumento) if argumento else 500
                    page.evaluate(f"window.scrollBy(0, -{cant})")
                    print(f"  Scroll arriba {cant}px")

                elif accion == "esperar":
                    segs = int(argumento) if argumento else 3
                    page.wait_for_timeout(segs * 1000)
                    print(f"  Esperé {segs}s")

                elif accion == "html":
                    _mostrar_html_resumido(page)

                elif accion == "buscar":
                    if not argumento:
                        print("  Uso: buscar TEXTO_PARCIAL")
                        continue
                    _buscar_en_pagina(page, argumento)

                elif accion == "guardar":
                    if not argumento:
                        print("  Uso: guardar NOMBRE_DEL_PASO")
                        continue
                    paso = _crear_paso(page, argumento)
                    receta["pasos"].append(paso)
                    print(f"  Paso '{argumento}' guardado ({len(receta['pasos'])} total)")

                elif accion == "receta":
                    _mostrar_receta(receta)

                elif accion == "atras" or accion == "back":
                    page.go_back(timeout=15_000)
                    page.wait_for_timeout(2000)
                    _mostrar_info(page)

                elif accion == "tabs":
                    _listar_tabs(context)

                elif accion == "tab":
                    if not argumento:
                        print("  Uso: tab NUMERO")
                        continue
                    idx = int(argumento) - 1
                    if 0 <= idx < len(context.pages):
                        page = context.pages[idx]
                        page.bring_to_front()
                        _mostrar_info(page)
                    else:
                        print(f"  Tab {argumento} no existe")

                else:
                    print(f"  Comando desconocido: '{accion}'. Escribe 'ayuda' para ver opciones.")

            except Exception as e:
                print(f"  [ERROR] {e}")

    except (KeyboardInterrupt, EOFError):
        print("\n  Cerrando...")

    finally:
        _guardar_receta(receta)
        print(f"\n[RECETA] Guardada en: {RECIPE_PATH} ({len(receta['pasos'])} pasos)")
        cerrar_navegador(pw, context)


# =============================================================
#  FUNCIONES AUXILIARES
# =============================================================

_ultimo_listado = []  # Guarda el último listado de enlaces para clickn


def _mostrar_ayuda():
    print("""
  Navegación:
    url URL          Navega a una dirección
    atras            Página anterior
    scroll [N]       Baja N pixeles (default 500)
    scrollup [N]     Sube N pixeles
    esperar N        Espera N segundos

  Explorar:
    listar / ls      Lista enlaces visibles (con números)
    listar-btn / btn Lista botones visibles
    buscar TEXTO     Busca elementos que contengan un texto
    html             Muestra estructura del DOM
    info / i         URL y título actual
    screenshot / ss  Captura de pantalla
    tabs             Lista pestañas abiertas
    tab N            Cambia a pestaña N

  Interactuar:
    click TEXTO      Click en elemento con ese texto
    clickn N         Click en enlace #N del último 'listar'
    clicksel CSS     Click en selector CSS

  Receta:
    guardar NOMBRE   Guarda paso actual en recipe.json
    receta           Muestra pasos guardados

  Otros:
    ayuda / h        Muestra esta ayuda
    salir / q        Guarda receta y cierra
""")


def _mostrar_info(page):
    print(f"  URL:    {page.url}")
    try:
        print(f"  Título: {page.title()}")
    except Exception:
        pass


def _screenshot(page) -> str:
    ts = datetime.now().strftime("%H%M%S")
    ruta = os.path.join(SCREENSHOTS_DIR, f"step_{ts}.png")
    page.screenshot(path=ruta, full_page=False)
    return ruta


def _hacer_click_texto(page, texto: str):
    selectores = [
        f"a:visible:has-text('{texto}')",
        f"button:visible:has-text('{texto}')",
        f"span:visible:has-text('{texto}')",
        f"div[role='button']:visible:has-text('{texto}')",
        f"[role='link']:visible:has-text('{texto}')",
        f"[role='menuitem']:visible:has-text('{texto}')",
    ]

    for sel in selectores:
        try:
            elem = page.locator(sel).first
            if elem.is_visible(timeout=2000):
                elem.click()
                page.wait_for_timeout(2000)
                print(f"  Click en: '{texto}'")
                _mostrar_info(page)
                return
        except Exception:
            continue

    print(f"  No encontré: '{texto}'")
    print("  Usa 'listar' para ver opciones, o 'buscar {texto}' para buscar en el DOM")


def _hacer_click_numero(page, numero: int):
    global _ultimo_listado
    if not _ultimo_listado:
        print("  Primero ejecuta 'listar' para obtener los enlaces")
        return
    if numero < 1 or numero > len(_ultimo_listado):
        print(f"  Número fuera de rango (1-{len(_ultimo_listado)})")
        return

    enlace = _ultimo_listado[numero - 1]
    try:
        enlace["elem"].click(timeout=5000)
        page.wait_for_timeout(2000)
        print(f"  Click en #{numero}: '{enlace['texto']}'")
        _mostrar_info(page)
    except Exception as e:
        print(f"  Error clickeando #{numero}: {e}")


def _hacer_click_selector(page, selector: str):
    page.locator(selector).first.click(timeout=5000)
    page.wait_for_timeout(2000)
    print(f"  Click en: {selector}")
    _mostrar_info(page)


def _listar_enlaces(page):
    global _ultimo_listado
    _ultimo_listado = []

    try:
        enlaces = page.locator("a:visible").all()
        items = []
        for link in enlaces:
            try:
                texto = (link.text_content() or "").strip()
                texto = " ".join(texto.split())[:70]  # Limpiar espacios
                href = (link.get_attribute("href") or "")[:80]
                if texto or (href and not href.startswith("javascript")):
                    items.append({"texto": texto, "href": href, "elem": link})
            except Exception:
                continue

        _ultimo_listado = items
        print(f"\n  Enlaces visibles ({len(items)}):")
        print(f"  {'#':>4}  {'Texto':<50} URL")
        print(f"  {'─'*4}  {'─'*50} {'─'*30}")
        for i, item in enumerate(items[:60], 1):
            txt = item['texto'][:50] if item['texto'] else "(sin texto)"
            print(f"  {i:4}  {txt:<50} {item['href'][:30]}")

        if len(items) > 60:
            print(f"  ... y {len(items) - 60} más")
        print(f"\n  Usa 'clickn N' para hacer click en un enlace por número")
    except Exception as e:
        print(f"  Error: {e}")


def _listar_botones(page):
    try:
        botones = page.locator("button:visible, [role='button']:visible, input[type='submit']:visible").all()
        print(f"\n  Botones visibles ({len(botones)}):")
        for i, btn in enumerate(botones[:30], 1):
            try:
                texto = (btn.text_content() or "").strip()
                texto = " ".join(texto.split())[:60]
                aria = btn.get_attribute("aria-label") or ""
                if texto or aria:
                    print(f"  {i:4}  {texto or aria}")
            except Exception:
                continue
    except Exception as e:
        print(f"  Error: {e}")


def _buscar_en_pagina(page, texto: str):
    try:
        resultados = page.evaluate("""(buscar) => {
            const results = [];
            const walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_ELEMENT
            );
            while (walker.nextNode()) {
                const el = walker.currentNode;
                const t = el.textContent || '';
                const directText = Array.from(el.childNodes)
                    .filter(n => n.nodeType === 3)
                    .map(n => n.textContent.trim())
                    .join(' ');
                if (directText.toLowerCase().includes(buscar.toLowerCase()) && directText.length < 200) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || '',
                            class: (el.className.toString() || '').substring(0, 40),
                            text: directText.substring(0, 80),
                            role: el.getAttribute('role') || '',
                            href: el.getAttribute('href') || ''
                        });
                    }
                }
            }
            return results.slice(0, 20);
        }""", texto)

        print(f"\n  Elementos con '{texto}' ({len(resultados)}):")
        for r in resultados:
            selector = f"<{r['tag']}"
            if r['id']:
                selector += f" id='{r['id']}'"
            if r['role']:
                selector += f" role='{r['role']}'"
            if r['href']:
                selector += f" href='{r['href'][:40]}'"
            selector += ">"
            print(f"  • {selector}")
            print(f"    texto: {r['text']}")
            if r['class']:
                print(f"    class: {r['class']}")
    except Exception as e:
        print(f"  Error: {e}")


def _mostrar_html_resumido(page):
    try:
        resumen = page.evaluate("""() => {
            const items = [];
            // Inputs visibles
            document.querySelectorAll('input:not([type="hidden"])').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0) {
                    items.push('INPUT: type=' + el.type +
                        ' placeholder="' + (el.placeholder || '') + '"' +
                        ' name="' + (el.name || '') + '"' +
                        ' id="' + (el.id || '') + '"');
                }
            });
            // Iframes
            document.querySelectorAll('iframe').forEach(el => {
                items.push('IFRAME: src=' + (el.src || '').substring(0, 80));
            });
            // Videos
            document.querySelectorAll('video, audio').forEach(el => {
                items.push(el.tagName + ': src=' + (el.src || el.querySelector('source')?.src || ''));
            });
            // Navigation / main areas
            document.querySelectorAll('nav, [role="navigation"], main, [role="main"]').forEach(el => {
                items.push(el.tagName + ': id=' + el.id + ' role=' + (el.getAttribute('role') || '') +
                    ' children=' + el.children.length);
            });
            return items.slice(0, 25);
        }""")
        print("\n  Estructura de la página:")
        for item in resumen:
            print(f"  • {item}")
        if not resumen:
            print("  (No se encontraron elementos destacados)")
    except Exception as e:
        print(f"  Error: {e}")


def _listar_tabs(context):
    pages = context.pages
    print(f"\n  Pestañas abiertas ({len(pages)}):")
    for i, p in enumerate(pages, 1):
        try:
            print(f"  {i}. {p.title()[:50]} — {p.url[:60]}")
        except Exception:
            print(f"  {i}. (sin acceso)")


def _crear_paso(page, nombre: str) -> dict:
    ruta_ss = _screenshot(page)
    nota = input("  Nota sobre este paso (Enter para omitir): ").strip()
    return {
        "nombre": nombre,
        "url": page.url,
        "titulo": page.title() if page.url != "about:blank" else "",
        "timestamp": datetime.now().isoformat(),
        "screenshot": os.path.basename(ruta_ss),
        "notas": nota,
    }


def _cargar_receta() -> dict:
    if os.path.exists(RECIPE_PATH):
        try:
            with open(RECIPE_PATH, "r", encoding="utf-8") as f:
                receta = json.load(f)
            print(f"[RECETA] Existente: {len(receta.get('pasos', []))} pasos")
            return receta
        except Exception:
            pass
    return {"plataforma": "aulavirtual.upc.edu.pe", "creada": datetime.now().isoformat(), "pasos": []}


def _guardar_receta(receta: dict):
    receta["actualizada"] = datetime.now().isoformat()
    with open(RECIPE_PATH, "w", encoding="utf-8") as f:
        json.dump(receta, f, ensure_ascii=False, indent=2)


def _mostrar_receta(receta: dict):
    pasos = receta.get("pasos", [])
    if not pasos:
        print("\n  Receta vacía. Usa 'guardar NOMBRE' para agregar pasos.")
        return
    print(f"\n  Receta ({len(pasos)} pasos):")
    for i, p in enumerate(pasos, 1):
        print(f"  {i}. [{p['nombre']}] — {p['url'][:60]}")
        if p.get("notas"):
            print(f"     Nota: {p['notas']}")


if __name__ == "__main__":
    main()
