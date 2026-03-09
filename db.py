"""
Módulo de persistencia con SQLite.
Registra el estado de cada curso y cada archivo descargado
para evitar duplicados y llevar trazabilidad.
"""
import sqlite3
from datetime import datetime
from config import DB_PATH


def _conectar() -> sqlite3.Connection:
    """Retorna una conexión a la base de datos, creando las tablas si no existen."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cursos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL,
            ciclo       TEXT NOT NULL,
            estado      TEXT NOT NULL DEFAULT 'pendiente',
            fecha_inicio TEXT,
            fecha_fin   TEXT,
            error       TEXT,
            UNIQUE(nombre, ciclo)
        );
        CREATE TABLE IF NOT EXISTS descargas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id    INTEGER NOT NULL,
            url         TEXT NOT NULL,
            archivo     TEXT NOT NULL,
            tipo        TEXT DEFAULT 'desconocido',
            fecha       TEXT NOT NULL,
            FOREIGN KEY (curso_id) REFERENCES cursos(id),
            UNIQUE(curso_id, url)
        );
    """)
    conn.commit()
    return conn


def registrar_cursos(cursos: list[dict]) -> None:
    """
    Inserta cursos nuevos (ignora duplicados).
    Espera lista de dicts con {nombre, ciclo}.
    """
    conn = _conectar()
    conn.executemany(
        "INSERT OR IGNORE INTO cursos (nombre, ciclo) VALUES (?, ?)",
        [(c["nombre"], c["ciclo"]) for c in cursos],
    )
    conn.commit()
    conn.close()


def obtener_cursos_pendientes() -> list[dict]:
    """Retorna cursos que aún no se han completado."""
    conn = _conectar()
    filas = conn.execute(
        "SELECT id, nombre, ciclo FROM cursos WHERE estado IN ('pendiente', 'error') ORDER BY id"
    ).fetchall()
    conn.close()
    return [{"id": f[0], "nombre": f[1], "ciclo": f[2]} for f in filas]


def obtener_todos_los_cursos() -> list[dict]:
    """Retorna todos los cursos registrados."""
    conn = _conectar()
    filas = conn.execute(
        "SELECT id, nombre, ciclo, estado, fecha_inicio, fecha_fin, error FROM cursos ORDER BY id"
    ).fetchall()
    conn.close()
    return [
        {"id": f[0], "nombre": f[1], "ciclo": f[2], "estado": f[3],
         "fecha_inicio": f[4], "fecha_fin": f[5], "error": f[6]}
        for f in filas
    ]


def marcar_curso(curso_id: int, estado: str, error: str | None = None) -> None:
    """Actualiza el estado de un curso: 'en_proceso', 'completado', 'error', 'sin_contenido'."""
    conn = _conectar()
    ahora = datetime.now().isoformat()
    if estado == "en_proceso":
        conn.execute(
            "UPDATE cursos SET estado=?, fecha_inicio=? WHERE id=?",
            (estado, ahora, curso_id),
        )
    elif estado in ("completado", "sin_contenido"):
        conn.execute(
            "UPDATE cursos SET estado=?, fecha_fin=? WHERE id=?",
            (estado, ahora, curso_id),
        )
    elif estado == "error":
        conn.execute(
            "UPDATE cursos SET estado=?, error=?, fecha_fin=? WHERE id=?",
            (estado, error, ahora, curso_id),
        )
    conn.commit()
    conn.close()


def ya_descargado(curso_id: int, url: str) -> bool:
    """Verifica si un enlace ya fue descargado para un curso."""
    conn = _conectar()
    existe = conn.execute(
        "SELECT 1 FROM descargas WHERE curso_id=? AND url=?", (curso_id, url)
    ).fetchone()
    conn.close()
    return existe is not None


def registrar_descarga(curso_id: int, url: str, archivo: str, tipo: str = "desconocido") -> None:
    """Registra un archivo descargado exitosamente."""
    conn = _conectar()
    conn.execute(
        "INSERT OR IGNORE INTO descargas (curso_id, url, archivo, tipo, fecha) VALUES (?,?,?,?,?)",
        (curso_id, url, archivo, tipo, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def contar_descargas(curso_id: int) -> int:
    """Cuenta cuántos archivos se han descargado para un curso."""
    conn = _conectar()
    count = conn.execute(
        "SELECT COUNT(*) FROM descargas WHERE curso_id=?", (curso_id,)
    ).fetchone()[0]
    conn.close()
    return count


def reporte() -> str:
    """Genera un resumen legible del estado de todos los cursos."""
    conn = _conectar()
    filas = conn.execute(
        "SELECT c.nombre, c.ciclo, c.estado, c.error, "
        "(SELECT COUNT(*) FROM descargas d WHERE d.curso_id = c.id) as num_descargas "
        "FROM cursos c ORDER BY c.ciclo, c.id"
    ).fetchall()
    conn.close()

    lineas = ["\n" + "=" * 70, "  REPORTE DE CURSOS — RPA_UPC MBA Salud", "=" * 70]

    ciclo_actual = ""
    for nombre, ciclo, estado, error, num_descargas in filas:
        if ciclo != ciclo_actual:
            ciclo_actual = ciclo
            lineas.append(f"\n  --- {ciclo} ---")

        icono = {
            "completado": "OK", "error": "ERR", "pendiente": "...",
            "en_proceso": ">>", "sin_contenido": "---"
        }.get(estado, "?")
        linea = f"  [{icono:^4}] {nombre[:50]:<50} ({num_descargas} archivos)"
        if error:
            linea += f"\n         Error: {error[:60]}"
        lineas.append(linea)

    lineas.append("\n" + "-" * 70)
    total = len(filas)
    completados = sum(1 for f in filas if f[2] == "completado")
    errores = sum(1 for f in filas if f[2] == "error")
    sin_contenido = sum(1 for f in filas if f[2] == "sin_contenido")
    pendientes = total - completados - errores - sin_contenido
    total_descargas = sum(f[4] for f in filas)

    lineas.append(
        f"  Total: {total} cursos | Completados: {completados} | "
        f"Sin contenido: {sin_contenido} | Errores: {errores} | Pendientes: {pendientes}"
    )
    lineas.append(f"  Total archivos descargados: {total_descargas}")
    lineas.append("=" * 70)
    return "\n".join(lineas)
