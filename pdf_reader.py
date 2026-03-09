"""
Módulo de lectura de PDF.
Extrae nombres de cursos desde un archivo PDF usando PyMuPDF.
Cada línea no vacía del PDF se considera un nombre de curso.
"""
import fitz  # PyMuPDF


def leer_cursos(ruta_pdf: str) -> list[str]:
    """
    Lee un PDF y retorna una lista de nombres de cursos.
    Ignora líneas vacías y elimina espacios extra.
    """
    cursos = []
    try:
        doc = fitz.open(ruta_pdf)
    except Exception as e:
        raise FileNotFoundError(f"No se pudo abrir el PDF: {ruta_pdf} — {e}")

    for pagina in doc:
        texto = pagina.get_text()
        for linea in texto.splitlines():
            limpia = linea.strip()
            # Ignorar líneas vacías, encabezados cortos o numeraciones sueltas
            if limpia and len(limpia) > 3 and not limpia.isdigit():
                cursos.append(limpia)

    doc.close()

    if not cursos:
        raise ValueError("El PDF no contiene nombres de cursos válidos.")

    print(f"[PDF] Se encontraron {len(cursos)} cursos en '{ruta_pdf}'")
    return cursos
