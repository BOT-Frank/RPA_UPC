"""
Módulo de descarga de archivos.
Descarga contenido multimedia y lo organiza en carpetas por curso en el disco E:.
"""
import os
import re
from playwright.sync_api import Page
import config
import db


def descargar_contenido(page: Page, curso_id: int, nombre_curso: str, enlaces: list[dict]) -> int:
    """
    Descarga cada enlace y lo guarda en E:\\RPA_Descargas\\<curso>\\.
    Retorna la cantidad de archivos descargados exitosamente.
    """
    # Crear carpeta del curso (sanitizar nombre para Windows)
    carpeta_curso = re.sub(r'[<>:"/\\|?*]', '_', nombre_curso)
    ruta_curso = os.path.join(config.DIRECTORIO_DESCARGAS, carpeta_curso)
    os.makedirs(ruta_curso, exist_ok=True)

    descargados = 0

    for enlace in enlaces:
        url = enlace["url"]
        nombre_archivo = enlace["nombre"]

        # Verificación extra de duplicados
        if db.ya_descargado(curso_id, url):
            print(f"  [SKIP] Ya descargado: {nombre_archivo}")
            continue

        ruta_destino = os.path.join(ruta_curso, nombre_archivo)

        # Evitar sobreescribir archivos existentes en disco
        if os.path.exists(ruta_destino):
            base, ext = os.path.splitext(nombre_archivo)
            contador = 1
            while os.path.exists(ruta_destino):
                ruta_destino = os.path.join(ruta_curso, f"{base}_{contador}{ext}")
                contador += 1

        try:
            # Usar el mecanismo de descarga de Playwright
            with page.expect_download(timeout=config.TIMEOUT_DESCARGA) as download_info:
                # Navegar al enlace para iniciar la descarga
                page.evaluate(f"() => window.open('{url}')")

            download = download_info.value
            download.save_as(ruta_destino)

            # Registrar en base de datos
            db.registrar_descarga(curso_id, url, ruta_destino)
            descargados += 1
            print(f"  [OK] Descargado: {nombre_archivo}")

        except Exception as e:
            # Si expect_download falla, intentar descarga directa via request
            try:
                descargado = _descarga_directa(page, url, ruta_destino)
                if descargado:
                    db.registrar_descarga(curso_id, url, ruta_destino)
                    descargados += 1
                    print(f"  [OK] Descargado (directo): {nombre_archivo}")
                else:
                    print(f"  [ERROR] No se pudo descargar: {nombre_archivo} — {e}")
            except Exception as e2:
                print(f"  [ERROR] Falló descarga directa: {nombre_archivo} — {e2}")

    print(f"[DOWNLOAD] {descargados}/{len(enlaces)} archivos descargados para '{nombre_curso}'")
    return descargados


def _descarga_directa(page: Page, url: str, ruta_destino: str) -> bool:
    """
    Descarga un archivo usando el API de requests del contexto de Playwright.
    Útil cuando el enlace no dispara el evento de descarga del navegador.
    """
    try:
        response = page.context.request.get(url)
        if response.ok:
            with open(ruta_destino, "wb") as f:
                f.write(response.body())
            return True
    except Exception:
        pass
    return False
