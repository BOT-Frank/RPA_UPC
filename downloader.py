"""
Módulo de descarga de archivos.
Descarga contenido multimedia y lo organiza en carpetas por ciclo y curso en el disco E:.

Estructura de carpetas:
  E:\RPA_Descargas\
    Ciclo 1\
      ETICA Y RESPONSABILIDAD SOCIAL\
        archivo1.mp4
        archivo2.pdf
      CONTABILIDAD GERENCIAL\
        ...
    Ciclo 2\
      ...
"""
import os
import re
from playwright.sync_api import Page
import config
import db


def descargar_contenido(
    page: Page,
    curso_id: int,
    nombre_curso: str,
    ciclo: str,
    enlaces: list[dict],
) -> int:
    """
    Descarga cada enlace y lo guarda en E:\\RPA_Descargas\\<ciclo>\\<curso>\\.
    Retorna la cantidad de archivos descargados exitosamente.
    """
    # Crear carpeta: E:\RPA_Descargas\Ciclo X\NOMBRE_CURSO\
    carpeta_ciclo = _sanitizar_carpeta(ciclo)
    carpeta_curso = _sanitizar_carpeta(nombre_curso)
    ruta_curso = os.path.join(config.DIRECTORIO_DESCARGAS, carpeta_ciclo, carpeta_curso)
    os.makedirs(ruta_curso, exist_ok=True)

    descargados = 0

    for i, enlace in enumerate(enlaces, 1):
        url = enlace["url"]
        nombre_archivo = enlace["nombre"]
        tipo = enlace.get("tipo", "desconocido")

        # Verificación de duplicados
        if db.ya_descargado(curso_id, url):
            print(f"  [SKIP] Ya descargado: {nombre_archivo}")
            continue

        ruta_destino = _ruta_unica(ruta_curso, nombre_archivo)

        print(f"  [{i}/{len(enlaces)}] Descargando: {nombre_archivo} ({tipo})")

        # Intentar descarga con Playwright (evento download)
        exito = _intentar_descarga_evento(page, url, ruta_destino)

        # Fallback: descarga directa via HTTP
        if not exito:
            exito = _descarga_directa(page, url, ruta_destino)

        if exito:
            db.registrar_descarga(curso_id, url, ruta_destino, tipo)
            descargados += 1
            print(f"  [OK] Guardado en: {ruta_destino}")
        else:
            print(f"  [ERROR] No se pudo descargar: {nombre_archivo}")

    print(f"[DOWNLOAD] {descargados}/{len(enlaces)} archivos para '{nombre_curso}'")
    return descargados


def _intentar_descarga_evento(page: Page, url: str, ruta_destino: str) -> bool:
    """Intenta descargar usando el evento de descarga de Playwright."""
    try:
        with page.expect_download(timeout=config.TIMEOUT_DESCARGA) as download_info:
            page.evaluate(f"() => window.open('{url}')")

        download = download_info.value
        download.save_as(ruta_destino)
        return True
    except Exception:
        return False


def _descarga_directa(page: Page, url: str, ruta_destino: str) -> bool:
    """Descarga un archivo usando el API de requests del contexto de Playwright."""
    try:
        response = page.context.request.get(url, timeout=config.TIMEOUT_DESCARGA)
        if response.ok and len(response.body()) > 0:
            with open(ruta_destino, "wb") as f:
                f.write(response.body())
            return True
    except Exception:
        pass
    return False


def _ruta_unica(carpeta: str, nombre_archivo: str) -> str:
    """Genera una ruta única para evitar sobreescribir archivos existentes."""
    ruta = os.path.join(carpeta, nombre_archivo)
    if not os.path.exists(ruta):
        return ruta

    base, ext = os.path.splitext(nombre_archivo)
    contador = 1
    while os.path.exists(ruta):
        ruta = os.path.join(carpeta, f"{base}_{contador}{ext}")
        contador += 1
    return ruta


def _sanitizar_carpeta(nombre: str) -> str:
    """Sanitiza nombre para usar como carpeta en Windows."""
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    nombre = nombre.strip('. ')
    return nombre[:100] if nombre else "sin_nombre"
