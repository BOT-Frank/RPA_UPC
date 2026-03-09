"""
Módulo de asistencia con IA (OpenAI GPT).
Se usa solo cuando es necesario:
- Identificar el nombre correcto de un curso en la plataforma
- Decidir qué enlaces son relevantes para descargar
- Clasificar contenido encontrado

DISEÑADO para minimizar tokens: prompts cortos, modelo económico (gpt-4o-mini).
"""
from openai import OpenAI
import config

_client = None


def _get_client() -> OpenAI:
    """Inicializa el cliente OpenAI solo cuando se necesita (lazy loading)."""
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY no configurada. Agrega tu key en el archivo .env"
            )
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def buscar_nombre_curso(nombre_pdf: str, opciones_plataforma: list[str]) -> str | None:
    """
    Dado un nombre de curso del PDF y las opciones visibles en la plataforma,
    retorna el nombre que mejor coincide. Usa GPT solo si no hay match exacto.

    Primero intenta match directo (sin IA), luego fuzzy con IA.
    """
    # Match exacto (case insensitive)
    nombre_upper = nombre_pdf.upper().strip()
    for opcion in opciones_plataforma:
        if opcion.upper().strip() == nombre_upper:
            return opcion

    # Match parcial (contiene el nombre)
    for opcion in opciones_plataforma:
        if nombre_upper in opcion.upper() or opcion.upper() in nombre_upper:
            return opcion

    # Solo si no hay match, usar GPT (minimiza tokens)
    try:
        client = _get_client()
        opciones_texto = "\n".join(f"- {o}" for o in opciones_plataforma[:20])
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    f"Curso buscado: '{nombre_pdf}'\n"
                    f"Opciones disponibles:\n{opciones_texto}\n\n"
                    "Responde SOLO con el nombre exacto de la opción que coincide, "
                    "o 'NINGUNO' si no hay match."
                ),
            }],
            max_tokens=100,
            temperature=0,
        )
        respuesta = response.choices[0].message.content.strip()
        if respuesta != "NINGUNO" and respuesta in opciones_plataforma:
            print(f"  [AI] Match encontrado: '{nombre_pdf}' → '{respuesta}'")
            return respuesta
    except Exception as e:
        print(f"  [AI] Error consultando GPT: {e}")

    return None


def clasificar_enlace(url: str, texto_enlace: str, nombre_curso: str) -> dict:
    """
    Clasifica un enlace para decidir si es relevante para descargar.
    Retorna: {"descargar": bool, "tipo": str, "razon": str}

    Primero intenta clasificar por reglas (sin IA), luego usa GPT.
    """
    url_lower = url.lower()
    texto_lower = texto_enlace.lower()

    # Reglas directas (sin IA)
    # — Videos/grabaciones: siempre descargar
    if any(ext in url_lower for ext in [".mp4", ".webm", ".mp3", "recording", "zoom.us/rec", "panopto"]):
        return {"descargar": True, "tipo": "video/grabación", "razon": "URL multimedia detectada"}

    # — Documentos: siempre descargar
    if any(ext in url_lower for ext in [".pdf", ".pptx", ".docx", ".xlsx", ".zip"]):
        return {"descargar": True, "tipo": "documento", "razon": "Documento detectado"}

    # — Recursos de Moodle/Blackboard
    if "pluginfile.php" in url_lower or "bbcswebdav" in url_lower:
        return {"descargar": True, "tipo": "recurso plataforma", "razon": "Archivo de plataforma"}

    # — Foros, wikis, tareas: no descargar
    if any(x in url_lower for x in ["forum", "assign", "quiz", "wiki", "chat"]):
        return {"descargar": False, "tipo": "actividad", "razon": "Actividad no descargable"}

    # — Enlaces de navegación: no descargar
    if any(x in url_lower for x in ["logout", "login", "calendar", "message", "notification"]):
        return {"descargar": False, "tipo": "navegación", "razon": "Enlace de navegación"}

    # Si no se puede determinar por reglas, usar GPT
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    f"URL: {url}\nTexto: {texto_enlace}\nCurso: {nombre_curso}\n\n"
                    "¿Este enlace contiene material descargable (video, grabación, "
                    "documento, presentación)? Responde JSON: "
                    '{"descargar": true/false, "tipo": "...", "razon": "..."}'
                ),
            }],
            max_tokens=80,
            temperature=0,
        )
        import json
        return json.loads(response.choices[0].message.content.strip())
    except Exception:
        # Por defecto, marcar como descargable si no podemos clasificar
        return {"descargar": True, "tipo": "desconocido", "razon": "No clasificado"}


def analizar_pagina_para_videos(html_content: str) -> list[str]:
    """
    Analiza HTML de una página para encontrar URLs de video embebidos
    que no se pueden detectar con selectores simples (iframes dinámicos, etc.).
    Solo se llama si los selectores normales no encuentran nada.

    Retorna lista de URLs encontradas.
    """
    # Primero intentar con regex (sin IA)
    import re
    urls = set()

    # Buscar URLs de video comunes en el HTML
    patrones = [
        r'https?://[^"\'\s]+\.mp4[^"\'\s]*',
        r'https?://[^"\'\s]*zoom\.us/rec/[^"\'\s]*',
        r'https?://[^"\'\s]*panopto[^"\'\s]*',
        r'https?://[^"\'\s]*kaltura[^"\'\s]*',
        r'https?://[^"\'\s]*mediasite[^"\'\s]*',
        r'https?://[^"\'\s]*recording[^"\'\s]*\.mp4',
    ]

    for patron in patrones:
        matches = re.findall(patron, html_content, re.IGNORECASE)
        urls.update(matches)

    if urls:
        return list(urls)

    # Si no encontramos nada con regex y el HTML es sospechoso de tener video,
    # usar GPT como último recurso (limitar a 2000 chars para ahorrar tokens)
    if any(kw in html_content.lower() for kw in ["video", "player", "recording", "grabación"]):
        try:
            client = _get_client()
            # Recortar HTML para ahorrar tokens
            html_recortado = html_content[:2000]
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Extrae las URLs de video de este HTML (solo URLs, una por línea):\n"
                        f"{html_recortado}"
                    ),
                }],
                max_tokens=200,
                temperature=0,
            )
            texto = response.choices[0].message.content.strip()
            for linea in texto.splitlines():
                linea = linea.strip().strip("-").strip()
                if linea.startswith("http"):
                    urls.add(linea)
        except Exception as e:
            print(f"  [AI] Error analizando HTML: {e}")

    return list(urls)
