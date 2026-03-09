"""
=======================================================
  RPA_UPC — Automatización de descarga de contenido
  MBA Administración de Empresas de Salud — UPC Perú
=======================================================

Uso:
    python main.py                  → Procesa todos los cursos pendientes
    python main.py --reporte        → Muestra estado de todos los cursos
    python main.py --reset          → Reinicia cursos con error a pendiente
    python main.py --ciclo 3        → Procesa solo el Ciclo 3
    python main.py --listar         → Lista los cursos extraídos de los PDFs

Flujo:
    1. Lee cursos de los PDFs de horarios (PDF_Ciclos/)
    2. Registra cursos en SQLite (evita duplicados)
    3. Abre Chrome con perfil "Diseñador" (Profile 4)
    4. Navega a aulavirtual.upc.edu.pe
    5. Por cada curso pendiente:
       a. Busca en la plataforma (con AI si no hay match exacto)
       b. Extrae enlaces multimedia/grabaciones
       c. Descarga a E:\\RPA_Descargas\\Ciclo X\\CURSO\\
       d. Registra en SQLite
    6. Muestra reporte final
"""
import sys
import config
from pdf_reader import obtener_lista_plana
from browser import abrir_navegador, cerrar_navegador
from navigator import navegar_a_plataforma, buscar_curso, extraer_enlaces_multimedia
from downloader import descargar_contenido
import db


def main():
    args = sys.argv[1:]

    # --- Modo reporte ---
    if "--reporte" in args:
        print(db.reporte())
        return

    # --- Modo listar cursos ---
    if "--listar" in args:
        cursos = obtener_lista_plana()
        print(f"\nTotal: {len(cursos)} cursos\n")
        ciclo_actual = ""
        for c in cursos:
            if c["ciclo"] != ciclo_actual:
                ciclo_actual = c["ciclo"]
                print(f"\n  --- {ciclo_actual} ---")
            print(f"    • {c['nombre']}")
        return

    # --- Modo reset ---
    if "--reset" in args:
        conn = db._conectar()
        conn.execute("UPDATE cursos SET estado='pendiente', error=NULL WHERE estado='error'")
        conn.commit()
        conn.close()
        print("[RESET] Cursos con error reiniciados a pendiente.")
        return

    # --- Filtro por ciclo ---
    ciclo_filtro = None
    if "--ciclo" in args:
        idx = args.index("--ciclo")
        if idx + 1 < len(args):
            ciclo_filtro = f"Ciclo {args[idx + 1]}"
            print(f"[FILTRO] Solo procesando: {ciclo_filtro}")

    # === PASO 1: Leer cursos de los PDFs ===
    print("\n" + "=" * 60)
    print("  RPA_UPC — MBA Salud — Inicio de procesamiento")
    print("=" * 60)

    try:
        todos_cursos = obtener_lista_plana()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # Filtrar por ciclo si se especificó
    if ciclo_filtro:
        todos_cursos = [c for c in todos_cursos if c["ciclo"] == ciclo_filtro]

    # === PASO 2: Registrar en base de datos ===
    db.registrar_cursos(todos_cursos)
    pendientes = db.obtener_cursos_pendientes()

    # Filtrar pendientes por ciclo si aplica
    if ciclo_filtro:
        pendientes = [p for p in pendientes if p["ciclo"] == ciclo_filtro]

    if not pendientes:
        print("[INFO] Todos los cursos ya fueron procesados.")
        print(db.reporte())
        return

    print(f"[INFO] {len(pendientes)} cursos pendientes de procesar.\n")

    # === PASO 3: Abrir navegador ===
    pw = context = page = None
    try:
        pw, context, page = abrir_navegador()
    except Exception as e:
        print(f"[ERROR] No se pudo abrir el navegador: {e}")
        print("  → Asegúrate de cerrar TODAS las ventanas de Chrome.")
        print("  → El perfil 'Diseñador' (Profile 4) no puede estar en uso.")
        sys.exit(1)

    # === PASO 4: Verificar sesión ===
    try:
        if not navegar_a_plataforma(page):
            print("[ERROR] Sin sesión activa en la plataforma.")
            print("  → Abre Chrome con el perfil 'Diseñador' e inicia sesión manualmente.")
            cerrar_navegador(pw, context)
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] No se pudo acceder a la plataforma: {e}")
        cerrar_navegador(pw, context)
        sys.exit(1)

    # === PASO 5: Procesar cada curso ===
    try:
        for i, curso in enumerate(pendientes, 1):
            curso_id = curso["id"]
            nombre = curso["nombre"]
            ciclo = curso["ciclo"]

            print(f"\n{'─' * 50}")
            print(f"[{i}/{len(pendientes)}] {ciclo} → {nombre}")
            print(f"{'─' * 50}")

            db.marcar_curso(curso_id, "en_proceso")

            try:
                # Buscar y entrar al curso
                encontrado = buscar_curso(page, nombre)
                if not encontrado:
                    db.marcar_curso(curso_id, "error", "Curso no encontrado en la plataforma")
                    continue

                # Extraer enlaces multimedia
                enlaces = extraer_enlaces_multimedia(page, curso_id, nombre)
                if not enlaces:
                    print(f"[INFO] Sin contenido multimedia nuevo en '{nombre}'")
                    db.marcar_curso(curso_id, "sin_contenido")
                    continue

                # Descargar contenido
                descargar_contenido(page, curso_id, nombre, ciclo, enlaces)
                db.marcar_curso(curso_id, "completado")

            except Exception as e:
                db.marcar_curso(curso_id, "error", str(e)[:200])
                print(f"[ERROR] Fallo en curso '{nombre}': {e}")
                continue

    finally:
        # === PASO 6: Cerrar navegador y mostrar reporte ===
        if pw and context:
            cerrar_navegador(pw, context)

    print(db.reporte())


if __name__ == "__main__":
    main()
