"""
=======================================================
  RPA_UPC — Script Principal
  Automatización de descarga de contenido educativo
=======================================================

Uso:
    python main.py              → Procesa todos los cursos pendientes
    python main.py --reporte    → Muestra el reporte de estado
    python main.py --reset      → Reinicia cursos con error a pendiente

Flujo:
    1. Lee nombres de cursos desde el PDF
    2. Registra cursos nuevos en SQLite
    3. Abre Chrome con perfil existente (sesión iniciada)
    4. Por cada curso pendiente:
       a. Busca el curso en la plataforma
       b. Extrae enlaces multimedia
       c. Descarga archivos al disco E:
       d. Registra resultado en SQLite
    5. Muestra reporte final
"""
import sys
import config
from pdf_reader import leer_cursos
from browser import abrir_navegador, cerrar_navegador
from navigator import buscar_curso, extraer_enlaces_multimedia
from downloader import descargar_contenido
import db


def main():
    # --- Modo reporte ---
    if "--reporte" in sys.argv:
        print(db.reporte())
        return

    # --- Modo reset de errores ---
    if "--reset" in sys.argv:
        conn = db._conectar()
        conn.execute("UPDATE cursos SET estado='pendiente', error=NULL WHERE estado='error'")
        conn.commit()
        conn.close()
        print("[RESET] Cursos con error reiniciados a pendiente.")
        return

    # === PASO 1: Leer cursos del PDF ===
    print("\n" + "=" * 50)
    print("  RPA_UPC — Inicio de procesamiento")
    print("=" * 50)

    try:
        nombres_cursos = leer_cursos(config.PDF_CURSOS)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # === PASO 2: Registrar en base de datos ===
    db.registrar_cursos(nombres_cursos)
    pendientes = db.obtener_cursos_pendientes()

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
        print("  → Asegúrate de que Chrome no esté abierto con el mismo perfil.")
        print("  → Cierra todas las ventanas de Chrome e intenta de nuevo.")
        sys.exit(1)

    # === PASO 4: Procesar cada curso ===
    try:
        for curso in pendientes:
            curso_id = curso["id"]
            nombre = curso["nombre"]
            print(f"\n{'─' * 40}")
            print(f"Procesando: {nombre}")
            print(f"{'─' * 40}")

            db.marcar_curso(curso_id, "en_proceso")

            try:
                # Buscar y entrar al curso
                encontrado = buscar_curso(page, nombre)
                if not encontrado:
                    db.marcar_curso(curso_id, "error", "Curso no encontrado en la plataforma")
                    continue

                # Extraer enlaces multimedia
                enlaces = extraer_enlaces_multimedia(page, curso_id)
                if not enlaces:
                    print(f"[INFO] Sin contenido multimedia nuevo en '{nombre}'")
                    db.marcar_curso(curso_id, "completado")
                    continue

                # Descargar contenido
                descargar_contenido(page, curso_id, nombre, enlaces)
                db.marcar_curso(curso_id, "completado")

            except Exception as e:
                db.marcar_curso(curso_id, "error", str(e)[:200])
                print(f"[ERROR] Fallo en curso '{nombre}': {e}")
                continue

    finally:
        # === PASO 5: Cerrar navegador y mostrar reporte ===
        if pw and context:
            cerrar_navegador(pw, context)

    print("\n" + db.reporte())


if __name__ == "__main__":
    main()
