# GUÍA DE DESPLIEGUE — RPA_UPC

## Arquitectura del Proyecto

```
RPA_UPC/
├── main.py            # Script principal (punto de entrada)
├── config.py          # Configuración central (rutas, URLs, tiempos)
├── pdf_reader.py      # Lectura de cursos desde PDF (PyMuPDF)
├── browser.py         # Gestión de Chrome con perfil existente (Playwright)
├── navigator.py       # Navegación en la plataforma educativa
├── downloader.py      # Descarga y organización de archivos
├── db.py              # Persistencia SQLite (registro de cursos/descargas)
├── cursos.pdf         # PDF con nombres de cursos (lo provees tú)
├── registro.db        # Base de datos SQLite (se crea automáticamente)
├── requirements.txt   # Dependencias Python
└── .gitignore
```

## Flujo del Sistema

```
cursos.pdf → pdf_reader → db (registra) → browser (abre Chrome)
    → navigator (busca curso → entra → extrae enlaces)
    → downloader (descarga a E:\) → db (registra descarga)
    → siguiente curso → reporte final
```

---

## Requisitos Previos

| Requisito | Versión mínima |
|-----------|---------------|
| Python | 3.11+ |
| Google Chrome | Instalado con sesión iniciada en la plataforma |
| Windows | 10/11 (por el disco E:) |
| Disco E: | Con espacio disponible |

---

## Paso 1: Clonar el repositorio

```bash
git clone <URL_DEL_REPO> RPA_UPC
cd RPA_UPC
```

## Paso 2: Crear entorno virtual

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

## Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

## Paso 4: Instalar navegador de Playwright

```bash
playwright install chromium
```

> **Nota:** Usamos `channel="chrome"` para conectar al Chrome instalado del sistema,
> pero Playwright necesita sus binarios base instalados.

## Paso 5: Configurar `config.py`

Abre `config.py` y ajusta estas variables según tu entorno:

```python
# Ruta al PDF con los nombres de cursos
PDF_CURSOS = "cursos.pdf"

# Directorio de descargas
DIRECTORIO_DESCARGAS = "E:\\RPA_Descargas"

# Perfil de Chrome (ajustar tu usuario de Windows)
CHROME_USER_DATA_DIR = "C:\\Users\\TU_USUARIO\\AppData\\Local\\Google\\Chrome\\User Data"
CHROME_PROFILE = "Default"  # o "Profile 1" si usas varios perfiles

# URL de la plataforma educativa
PLATAFORMA_URL = "https://aulavirtual.upc.edu.pe"
```

### ¿Cómo encontrar tu perfil de Chrome?

1. Abre Chrome y navega a `chrome://version`
2. Busca **"Profile Path"** → ejemplo: `C:\Users\Juan\AppData\Local\Google\Chrome\User Data\Default`
3. `CHROME_USER_DATA_DIR` = todo hasta `User Data`
4. `CHROME_PROFILE` = la última carpeta (`Default`, `Profile 1`, etc.)

## Paso 6: Preparar el PDF de cursos

Crea un archivo `cursos.pdf` en la raíz del proyecto. Cada línea del PDF debe tener el nombre exacto de un curso tal como aparece en la plataforma. Ejemplo:

```
Cálculo 1
Física 2
Programación Orientada a Objetos
Bases de Datos
```

## Paso 7: Cerrar Chrome

**IMPORTANTE:** Cierra todas las ventanas de Chrome antes de ejecutar el script.
Playwright no puede usar un perfil que ya está en uso por otra instancia de Chrome.

## Paso 8: Ejecutar

```bash
python main.py
```

El sistema:
1. Lee los cursos del PDF
2. Abre Chrome con tu sesión existente (ya logueado)
3. Busca cada curso en la plataforma
4. Extrae y descarga contenido multimedia
5. Guarda todo en `E:\RPA_Descargas\<nombre_curso>\`
6. Muestra un reporte al finalizar

---

## Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `python main.py` | Ejecutar el proceso completo |
| `python main.py --reporte` | Ver estado de todos los cursos |
| `python main.py --reset` | Reiniciar cursos con error a pendiente |

---

## Personalización de Selectores (CRÍTICO)

El archivo `navigator.py` contiene selectores CSS marcados con `--- PERSONALIZAR ---`.
Estos selectores dependen del DOM real de la plataforma educativa.

**Para ajustarlos:**

1. Abre Chrome manualmente
2. Ve a la plataforma educativa
3. Haz clic derecho → "Inspeccionar" en:
   - El campo de búsqueda de cursos
   - Los enlaces a los cursos en resultados de búsqueda
   - Los enlaces a recursos/grabaciones dentro de un curso
4. Copia los selectores CSS correctos
5. Reemplázalos en `navigator.py`

---

## Base de Datos SQLite

El archivo `registro.db` se crea automáticamente y tiene 2 tablas:

**cursos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | PK autoincremental |
| nombre | TEXT | Nombre del curso |
| estado | TEXT | pendiente / en_proceso / completado / error |
| fecha_inicio | TEXT | Timestamp de inicio |
| fecha_fin | TEXT | Timestamp de finalización |
| error | TEXT | Mensaje de error (si aplica) |

**descargas:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | PK autoincremental |
| curso_id | INTEGER | FK a cursos |
| url | TEXT | URL de origen |
| archivo | TEXT | Ruta local del archivo |
| fecha | TEXT | Timestamp de descarga |

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "No se pudo abrir el navegador" | Cierra todas las ventanas de Chrome e intenta de nuevo |
| "Curso no encontrado" | Verifica que el nombre en el PDF sea idéntico al de la plataforma |
| Selectores no funcionan | Inspecciona el DOM y actualiza los selectores en `navigator.py` |
| Descarga falla | Revisa que el disco E: tenga espacio y permisos de escritura |
| Timeout en navegación | Aumenta `TIMEOUT_NAVEGACION` en `config.py` |

---

## Notas de Seguridad

- El script usa tu perfil real de Chrome → **no compartas `registro.db`** ya que puede contener URLs con tokens
- No se almacenan credenciales en el código
- Las cookies y sesión se manejan a través del perfil de Chrome existente
