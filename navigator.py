"""
Módulo de navegación en la plataforma educativa UPC.
URL: https://aulavirtual.upc.edu.pe

La plataforma de UPC usa Blackboard Learn.
Este módulo busca cursos, entra a ellos e identifica contenido multimedia.

NOTA: Los selectores se ajustarán al DOM real de Blackboard UPC.
Secciones marcadas con [AJUSTAR] requieren verificación contra el DOM real.
"""
import os
import re
from urllib.parse import urlparse, unquote
from playwright.sync_api import Page, TimeoutError as PwTimeout
import config
import db
import ai_helper


def navegar_a_plataforma(page: Page) -> bool:
    """Navega a la página principal y verifica que hay sesión activa."""
    print("[NAV] Accediendo a la plataforma UPC...")
    page.goto(config.PLATAFORMA_URL, timeout=config.TIMEOUT_NAVEGACION)
    page.wait_for_load_state("domcontentloaded")

    # Verificar si hay sesión activa (no redirigió a login)
    url_actual = page.url.lower()
    if "login" in url_actual or "auth" in url_actual:
        print("[NAV] ⚠ No hay sesión activa. Inicia sesión manualmente en Chrome primero.")
        return False

    print("[NAV] Sesión activa detectada.")
    return True


def buscar_curso(page: Page, nombre_curso: str) -> bool:
    """
    Busca un curso en la plataforma y entra a él.
    Estrategia:
    1. Ir a la lista de cursos
    2. Buscar por nombre
    3. Si no hay match exacto, usar AI para identificar el correcto
    """
    print(f"[NAV] Buscando curso: '{nombre_curso}'")

    # [AJUSTAR] URL de lista de cursos en Blackboard UPC
    # Blackboard típico: /ultra/institution-page / /webapps/portal/execute/tabs/tabAction
    urls_intentar = [
        f"{config.PLATAFORMA_URL}/ultra/institution-page",
        f"{config.PLATAFORMA_URL}/ultra/course",
        f"{config.PLATAFORMA_URL}/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1",
        config.PLATAFORMA_URL,
    ]

    for url in urls_intentar:
        try:
            page.goto(url, timeout=config.TIMEOUT_NAVEGACION)
            page.wait_for_load_state("domcontentloaded")
            break
        except Exception:
            continue

    # [AJUSTAR] Buscar campo de búsqueda y escribir el nombre del curso
    # Blackboard Ultra tiene un buscador en la página principal
    selectores_busqueda = [
        "input[placeholder*='Buscar']",
        "input[placeholder*='Search']",
        "input[data-testid*='search']",
        "input.search-input",
        "input#search-field",
        "#courseSearchBox",
        "input[type='search']",
    ]

    campo = None
    for selector in selectores_busqueda:
        try:
            campo = page.locator(selector).first
            if campo.is_visible(timeout=3000):
                break
            campo = None
        except Exception:
            campo = None

    if campo:
        campo.fill(nombre_curso)
        campo.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)  # Esperar resultados
    else:
        print("[NAV] No se encontró campo de búsqueda. Buscando en la lista directamente...")

    # [AJUSTAR] Buscar el enlace al curso en los resultados
    # Blackboard muestra los cursos como enlaces con el nombre
    selectores_curso = [
        f"a:has-text('{nombre_curso}')",
        f"a[title*='{nombre_curso}']",
        f"[data-course-name*='{nombre_curso}']",
        f".course-element:has-text('{nombre_curso}') a",
        f"a.courseListing:has-text('{nombre_curso}')",
    ]

    for selector in selectores_curso:
        try:
            enlace = page.locator(selector).first
            if enlace.is_visible(timeout=3000):
                enlace.click()
                page.wait_for_load_state("domcontentloaded")
                print(f"[NAV] Entró al curso: '{nombre_curso}'")
                return True
        except Exception:
            continue

    # Si no encontramos match exacto, obtener todos los enlaces visibles
    # y usar AI para encontrar el mejor match
    try:
        enlaces_visibles = page.locator("a").all_text_contents()
        # Filtrar solo los que parecen nombres de cursos (más de 10 caracteres)
        opciones = [t.strip() for t in enlaces_visibles if len(t.strip()) > 10]

        if opciones:
            match = ai_helper.buscar_nombre_curso(nombre_curso, opciones[:30])
            if match:
                page.locator(f"a:has-text('{match}')").first.click()
                page.wait_for_load_state("domcontentloaded")
                print(f"[NAV] Entró al curso via AI: '{match}'")
                return True
    except Exception as e:
        print(f"[NAV] Error buscando con AI: {e}")

    print(f"[NAV] No se encontró el curso: '{nombre_curso}'")
    return False


def extraer_enlaces_multimedia(page: Page, curso_id: int, nombre_curso: str) -> list[dict]:
    """
    Recorre las secciones del curso buscando contenido multimedia.
    Retorna lista de dicts con {url, nombre, tipo}.
    """
    enlaces = []
    page.wait_for_timeout(2000)

    # Paso 1: Buscar enlaces directos en la página del curso
    _buscar_en_pagina(page, curso_id, nombre_curso, enlaces)

    # Paso 2: Buscar en subpáginas (contenido, recursos, grabaciones)
    # [AJUSTAR] Selectores para secciones de contenido en Blackboard
    selectores_secciones = [
        "a[href*='content']",
        "a[href*='listContent']",
        "a[href*='resource']",
        "a[href*='streaming']",
        "a[href*='recording']",
        "a[href*='collaborate']",
        ".content-link a",
        "a.item-link",
    ]

    subpaginas_visitadas = set()

    for selector in selectores_secciones:
        try:
            links = page.locator(selector).all()
            for link in links[:30]:  # Límite para evitar bucles
                href = link.get_attribute("href")
                if not href or href in subpaginas_visitadas:
                    continue
                if any(x in href.lower() for x in ["logout", "login", "javascript"]):
                    continue

                subpaginas_visitadas.add(href)

                try:
                    subpage = page.context.new_page()
                    subpage.goto(href, timeout=config.TIMEOUT_NAVEGACION)
                    subpage.wait_for_load_state("domcontentloaded")
                    subpage.wait_for_timeout(1500)

                    _buscar_en_pagina(subpage, curso_id, nombre_curso, enlaces)

                    # Si no encontramos nada, intentar analizar el HTML con AI
                    if not enlaces:
                        html = subpage.content()
                        urls_ai = ai_helper.analizar_pagina_para_videos(html)
                        for url in urls_ai:
                            if not db.ya_descargado(curso_id, url):
                                enlaces.append({
                                    "url": url,
                                    "nombre": _extraer_nombre_archivo(url),
                                    "tipo": "video (AI)",
                                })

                    subpage.close()
                except Exception:
                    try:
                        subpage.close()
                    except Exception:
                        pass
        except Exception:
            continue

    # Deduplicar por URL
    vistos = set()
    unicos = []
    for e in enlaces:
        if e["url"] not in vistos:
            vistos.add(e["url"])
            unicos.append(e)

    print(f"[NAV] Encontrados {len(unicos)} enlaces multimedia nuevos en '{nombre_curso}'")
    return unicos


def _buscar_en_pagina(page: Page, curso_id: int, nombre_curso: str, enlaces: list) -> None:
    """Busca enlaces multimedia en una página específica."""

    # Selectores para contenido multimedia
    selectores = {
        "video": [
            "video source[src]",
            "a[href*='.mp4']",
            "a[href*='.webm']",
            "a[href*='.mp3']",
        ],
        "grabación": [
            "a[href*='recording']",
            "a[href*='zoom.us/rec']",
            "a[href*='panopto']",
            "a[href*='collaborate/recording']",
            "a[href*='kaltura']",
        ],
        "documento": [
            "a[href*='pluginfile.php']",
            "a[href*='bbcswebdav']",
            "a[href*='.pdf']",
            "a[href*='.pptx']",
            "a[href*='.docx']",
            "a[href*='.xlsx']",
            "a[href*='.zip']",
        ],
        "iframe": [
            "iframe[src*='youtube']",
            "iframe[src*='vimeo']",
            "iframe[src*='panopto']",
            "iframe[src*='kaltura']",
            "iframe[src*='mediasite']",
        ],
    }

    for tipo, sels in selectores.items():
        for selector in sels:
            try:
                elementos = page.locator(selector).all()
                for elem in elementos:
                    url = elem.get_attribute("href") or elem.get_attribute("src") or ""
                    if not url or url.startswith("#") or url.startswith("javascript"):
                        continue

                    if db.ya_descargado(curso_id, url):
                        continue

                    # Usar AI para clasificar si no es obvio
                    texto = ""
                    try:
                        texto = elem.text_content() or ""
                    except Exception:
                        pass

                    clasificacion = ai_helper.clasificar_enlace(url, texto, nombre_curso)
                    if clasificacion["descargar"]:
                        nombre = _extraer_nombre_archivo(url, texto)
                        enlaces.append({
                            "url": url,
                            "nombre": nombre,
                            "tipo": clasificacion.get("tipo", tipo),
                        })
            except Exception:
                continue


def _extraer_nombre_archivo(url: str, texto: str = "") -> str:
    """Intenta obtener un nombre de archivo legible."""
    parsed = urlparse(url)
    nombre = os.path.basename(unquote(parsed.path))
    if nombre and "." in nombre and len(nombre) > 3:
        return _sanitizar_nombre(nombre)

    if texto and len(texto.strip()) > 3:
        return _sanitizar_nombre(texto.strip()[:80])

    return f"archivo_{abs(hash(url)) % 100000}"


def _sanitizar_nombre(nombre: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo en Windows."""
    nombre = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', nombre)
    nombre = nombre.strip('. ')
    return nombre[:200] if nombre else "sin_nombre"
