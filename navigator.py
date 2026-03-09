"""
Módulo de navegación en la plataforma educativa.
Busca cursos, entra a ellos e identifica contenido multimedia/grabaciones.

IMPORTANTE: Los selectores CSS usados aquí son PLACEHOLDERS.
Debes ajustarlos al DOM real de la plataforma (Moodle/Blackboard/Canvas/etc).
Se incluyen comentarios indicando dónde personalizar.
"""
import os
import re
from urllib.parse import urlparse, unquote
from playwright.sync_api import Page, TimeoutError as PwTimeout
import config
import db


def buscar_curso(page: Page, nombre_curso: str) -> bool:
    """
    Navega a la página de búsqueda y busca el curso por nombre.
    Retorna True si encontró y entró al curso.
    """
    print(f"[NAV] Buscando curso: '{nombre_curso}'")
    page.goto(config.BUSQUEDA_URL, timeout=config.TIMEOUT_NAVEGACION)
    page.wait_for_load_state("domcontentloaded")

    # --- PERSONALIZAR: selector del campo de búsqueda ---
    campo_busqueda = page.locator("input#coursesearchbox, input[name='search'], input.search-input").first
    campo_busqueda.fill(nombre_curso)
    campo_busqueda.press("Enter")
    page.wait_for_load_state("domcontentloaded")

    # --- PERSONALIZAR: selector del enlace al curso en resultados ---
    enlace_curso = page.locator(f"a.coursename:has-text('{nombre_curso}'), a[data-courseid]:has-text('{nombre_curso}'), .course-listing a:has-text('{nombre_curso}')").first

    try:
        enlace_curso.wait_for(timeout=10_000)
        enlace_curso.click()
        page.wait_for_load_state("domcontentloaded")
        print(f"[NAV] Entró al curso: '{nombre_curso}'")
        return True
    except PwTimeout:
        print(f"[NAV] No se encontró el curso: '{nombre_curso}'")
        return False


def extraer_enlaces_multimedia(page: Page, curso_id: int) -> list[dict]:
    """
    Recorre las secciones/páginas del curso buscando contenido multimedia.
    Retorna lista de dicts con {url, nombre_archivo}.
    """
    enlaces = []

    # --- PERSONALIZAR: selectores de enlaces a recursos multimedia ---
    # Buscar enlaces a archivos multimedia, grabaciones, videos embebidos
    selectores = [
        "a[href*='.mp4']",
        "a[href*='.mp3']",
        "a[href*='.webm']",
        "a[href*='pluginfile.php']",
        "a[href*='resource']",
        "a[href*='recording']",
        "a[href*='zoom.us/rec']",
        "a[href*='panopto']",
        "video source[src]",
        "iframe[src*='youtube'], iframe[src*='vimeo'], iframe[src*='panopto']",
    ]

    for selector in selectores:
        elementos = page.locator(selector).all()
        for elem in elementos:
            try:
                url = elem.get_attribute("href") or elem.get_attribute("src") or ""
                if not url or url.startswith("#") or url.startswith("javascript"):
                    continue

                # Evitar duplicados ya descargados
                if db.ya_descargado(curso_id, url):
                    continue

                nombre = _extraer_nombre_archivo(url, elem)
                enlaces.append({"url": url, "nombre": nombre})
            except Exception:
                continue

    # Buscar en subpáginas de actividades (ej: páginas de recursos)
    # --- PERSONALIZAR: selectores de enlaces a subpáginas ---
    links_actividades = page.locator(
        "a.aalink[href*='mod/resource'], a.aalink[href*='mod/page'], a.aalink[href*='mod/url']"
    ).all()

    for link in links_actividades[:50]:  # Límite para evitar bucles largos
        try:
            href = link.get_attribute("href")
            if not href:
                continue
            subpage = page.context.new_page()
            subpage.goto(href, timeout=config.TIMEOUT_NAVEGACION)
            subpage.wait_for_load_state("domcontentloaded")

            # Buscar multimedia en la subpágina
            for selector in selectores[:6]:
                sub_elems = subpage.locator(selector).all()
                for elem in sub_elems:
                    url = elem.get_attribute("href") or elem.get_attribute("src") or ""
                    if url and not db.ya_descargado(curso_id, url):
                        nombre = _extraer_nombre_archivo(url, elem)
                        enlaces.append({"url": url, "nombre": nombre})

            subpage.close()
        except Exception:
            continue

    print(f"[NAV] Encontrados {len(enlaces)} enlaces multimedia nuevos.")
    return enlaces


def _extraer_nombre_archivo(url: str, elemento) -> str:
    """Intenta obtener un nombre de archivo legible desde la URL o el texto del elemento."""
    # Intentar desde la URL
    parsed = urlparse(url)
    nombre = os.path.basename(unquote(parsed.path))
    if nombre and "." in nombre:
        return _sanitizar_nombre(nombre)

    # Intentar desde el texto del enlace
    try:
        texto = elemento.text_content() or ""
        texto = texto.strip()[:80]
        if texto:
            return _sanitizar_nombre(texto)
    except Exception:
        pass

    # Fallback
    return f"archivo_{hash(url) % 100000}"


def _sanitizar_nombre(nombre: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo en Windows."""
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    nombre = nombre.strip('. ')
    return nombre[:200] if nombre else "sin_nombre"
