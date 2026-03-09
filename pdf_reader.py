"""
Módulo de lectura de PDF.
Extrae nombres de cursos desde los horarios de MBA Salud UPC.
Los PDFs tienen formato de tabla con columna "Cursos" al inicio de cada página.
"""
import os
import re
import fitz  # PyMuPDF
import config


# Nombres conocidos de cursos extraídos de los PDFs de cada ciclo.
# Se usa como fuente primaria para evitar errores de parsing en tablas complejas.
CURSOS_POR_CICLO = {
    "Ciclo 1": [
        "ETICA Y RESPONSABILIDAD SOCIAL",
        "EL SECTOR: POLITICAS Y SISTEMAS DE SALUD. TENDENCIAS DEL MERCADO",
        "CONTABILIDAD GERENCIAL",
        "ECONOMIA DE LA SALUD",
        "COMPORTAMIENTO ORGANIZACIONAL",
        "METODOS CUANTITATIVOS",
    ],
    "Ciclo 2": [
        "OPERACIONES EN EMPRESAS DE SALUD",
        "EPIDEMIOLOGIA GERENCIAL",
        "GERENCIA DE LA CALIDAD Y DISEÑO DE PROCESOS DE SALUD",
        "TIC APLICADAS A LOS SERVICIOS DE SALUD",
        "GERENCIA DEL POTENCIAL HUMANO",
    ],
    "Ciclo 3": [
        "MARKETING ORIENTADO AL CLIENTE",
        "GERENCIA AVANZADA DE LOGISTICA",
        "LIDERAZGO DE EQUIPOS DE ALTO RENDIMIENTO",
        "ADMINISTRACION DE COSTOS Y PRESUPUESTOS",
        "COBERTURA UNIVERSAL EN SALUD",
        "LA GERENCIA EN EMPRESAS FAMILIARES",
    ],
    "Ciclo 4": [
        "DERECHO MEDICO Y BIOETICA",
        "COMUNICACION COMO ESTRATEGIA Y MANEJO DE CRISIS: MEDIA TRAINING",
        "FINANZAS CORPORATIVAS Y CREACION DE VALOR",
        "AUDITORIA EN SALUD PARA UNA GESTION EFICIENTE",
        "NEGOCIACIONES",
    ],
    "Ciclo 5": [
        "GERENCIA COMERCIAL EN EMPRESAS DE SERVICIOS",
        "GERENCIA DEL RIESGO EN ORGANIZACIONES DE SALUD I",
        "BALANCED SCORECARD",
        "GERENCIA SOCIAL EN SALUD",
        "EVALUACION ECONOMICA DE PROYECTOS EN SALUD",
        "EMPRENDIMIENTO EN NUEVOS NEGOCIOS",
        "TESIS I",
    ],
    "Ciclo 6": [
        "DIRECCION ESTRATEGICA DE MARKETING",
        "GERENCIA DE PROYECTOS DE INVERSION EN SALUD",
        "SOCIEDADES Y TRIBUTACION",
        "DIRECCION ESTRATEGICA DE EMPRESAS DE SALUD",
        "SIMULADOR DE VUELO GERENCIAL",
        "GERENCIA DEL RIESGO EN ORGANIZACIONES DE SALUD II",
        "TESIS II",
    ],
}


def leer_todos_los_ciclos() -> dict[str, list[str]]:
    """
    Retorna un dict {ciclo: [cursos]} leyendo los PDFs de PDF_Ciclos/.
    Usa el mapeo hardcodeado como fuente principal (los PDFs son tablas complejas),
    pero valida que los archivos PDF existan.
    """
    pdf_dir = config.PDF_CICLOS_DIR
    if not os.path.isdir(pdf_dir):
        raise FileNotFoundError(f"No se encontró la carpeta: {pdf_dir}")

    archivos = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    if not archivos:
        raise FileNotFoundError(f"No hay archivos PDF en: {pdf_dir}")

    print(f"[PDF] Encontrados {len(archivos)} archivos PDF en '{pdf_dir}'")
    for f in sorted(archivos):
        print(f"  - {f}")

    # Retornar cursos conocidos, excluyendo misiones académicas e inducción
    resultado = {}
    total = 0
    for ciclo, cursos in CURSOS_POR_CICLO.items():
        cursos_filtrados = [
            c for c in cursos
            if not any(excl in c.upper() for excl in config.CURSOS_EXCLUIR)
        ]
        resultado[ciclo] = cursos_filtrados
        total += len(cursos_filtrados)

    print(f"[PDF] Total: {total} cursos en {len(resultado)} ciclos")
    return resultado


def obtener_lista_plana() -> list[dict]:
    """
    Retorna una lista plana de cursos con su ciclo para procesamiento.
    Formato: [{"nombre": "CURSO X", "ciclo": "Ciclo 1"}, ...]
    """
    ciclos = leer_todos_los_ciclos()
    cursos = []
    for ciclo, nombres in ciclos.items():
        for nombre in nombres:
            cursos.append({"nombre": nombre, "ciclo": ciclo})
    return cursos


def extraer_cursos_de_pdf(ruta_pdf: str) -> list[str]:
    """
    Intenta extraer nombres de cursos del texto del PDF (tabla superior).
    Se usa como verificación o para PDFs con formato diferente.
    """
    cursos = set()
    doc = fitz.open(ruta_pdf)

    for pagina in doc:
        texto = pagina.get_text()
        for linea in texto.splitlines():
            limpia = linea.strip()
            # Las líneas de cursos en la tabla tienen "Ciclo N" como parte
            if re.match(r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s:.,\-()]+$', limpia) and len(limpia) > 10:
                # Excluir líneas que son metadatos
                excluir = ["MAESTRIA", "CAMPUS", "MODALIDAD", "VIERNES", "SABADO",
                           "PRESENCIAL", "VIRTUAL", "ONLINE", "EXPOSITORES"]
                if not any(e in limpia for e in excluir):
                    cursos.add(limpia)

    doc.close()
    return sorted(cursos)
