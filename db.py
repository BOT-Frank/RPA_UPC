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
            nombre      TEXT UNIQUE NOT NULL,
            estado      TEXT NOT NULL DEFAULT 'pendiente',
            fecha_inicio TEXT,
            fecha_fin   TEXT,
            error       TEXT
        );
        CREATE TABLE IF NOT EXISTS descargas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id    INTEGER NOT NULL,
            url         TEXT NOT NULL,
            archivo     TEXT NOT NULL,
            fecha       TEXT NOT NULL,
            FOREIGN KEY (curso_id) REFERENCES cursos(id),
            UNIQUE(curso_id, url)
        );
    """)
    conn.commit()
    return conn


def registrar_cursos(nombres: list[str]) -> None:
    """Inserta cursos nuevos (ignora duplicados)."""
    conn = _conectar()
    conn.executemany(
        "INSERT OR IGNORE INTO cursos (nombre) VALUES (?)",
        [(n,) for n in nombres],
    )
    conn.commit()
    conn.close()


def obtener_cursos_pendientes() -> list[dict]:
    """Retorna cursos que aún no se han completado."""
    conn = _conectar()
    filas = conn.execute(
        "SELECT id, nombre FROM cursos WHERE estado IN ('pendiente', 'error')"
    ).fetchall()
    conn.close()
    return [{"id": f[0], "nombre": f[1]} for f in filas]


def marcar_curso(curso_id: int, estado: str, error: str | None = None) -> None:
    """Actualiza el estado de un curso: 'en_proceso', 'completado', 'error'."""
    conn = _conectar()
    ahora = datetime.now().isoformat()
    if estado == "en_proceso":
        conn.execute(
            "UPDATE cursos SET estado=?, fecha_inicio=? WHERE id=?",
            (estado, ahora, curso_id),
        )
    elif estado == "completado":
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


def registrar_descarga(curso_id: int, url: str, archivo: str) -> None:
    """Registra un archivo descargado exitosamente."""
    conn = _conectar()
    conn.execute(
        "INSERT OR IGNORE INTO descargas (curso_id, url, archivo, fecha) VALUES (?,?,?,?)",
        (curso_id, url, archivo, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def reporte() -> str:
    """Genera un resumen legible del estado de todos los cursos."""
    conn = _conectar()
    filas = conn.execute(
        "SELECT nombre, estado, fecha_inicio, fecha_fin, error FROM cursos ORDER BY id"
    ).fetchall()
    conn.close()
    lineas = ["=" * 60, "REPORTE DE CURSOS", "=" * 60]
    for nombre, estado, inicio, fin, error in filas:
        linea = f"  [{estado.upper():^12}] {nombre}"
        if error:
            linea += f"  | Error: {error}"
        lineas.append(linea)
    lineas.append("=" * 60)
    total = len(filas)
    completados = sum(1 for f in filas if f[1] == "completado")
    lineas.append(f"Total: {total} | Completados: {completados} | Pendientes: {total - completados}")
    return "\n".join(lineas)
