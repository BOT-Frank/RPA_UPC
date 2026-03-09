# GUIA DE DESPLIEGUE — RPA_UPC

## Arquitectura del Proyecto

```
RPA_UPC/
├── main.py              # Script principal — punto de entrada
├── config.py            # Configuración (rutas, Chrome Profile 4, API keys)
├── pdf_reader.py        # Cursos extraídos de los PDFs de horarios MBA Salud
├── browser.py           # Gestión de Chrome con perfil "Diseñador"
├── navigator.py         # Navegación en aulavirtual.upc.edu.pe (Blackboard)
├── downloader.py        # Descarga y organización en disco E:
├── db.py                # SQLite — registro de cursos y descargas
├── ai_helper.py         # Integración GPT-4o-mini (match cursos, clasificación)
├── requirements.txt     # Dependencias Python
├── .env                 # API key de OpenAI (NO se sube a git)
├── .env.example         # Plantilla del .env
├── registro.db          # Base de datos (se crea automáticamente)
└── PDF_Ciclos/          # PDFs de horarios (6 ciclos MBA Salud)
    ├── Horario 1er ciclo MBA Salud 24v1.pdf
    ├── Horario 2do ciclo MBA Salud 24v1.pdf
    ├── Horario 3er Ciclo MBA Salud 24v1.pdf
    ├── Horario 4to Ciclo MBA Salud 24v1.pdf
    ├── Horario 5to ciclo MBA Salud 24v1.pdf
    └── Horario 6to ciclo MBA Salud 24v1.pdf
```

## Cursos detectados (37 cursos, 6 ciclos)

**Ciclo 1:** Ética y Resp. Social, Políticas y Sistemas de Salud, Contabilidad Gerencial, Economía de la Salud, Comportamiento Organizacional, Métodos Cuantitativos

**Ciclo 2:** Operaciones en Empresas de Salud, Epidemiología Gerencial, Gerencia de la Calidad, TIC Aplicadas, Gerencia del Potencial Humano

**Ciclo 3:** Marketing al Cliente, Gerencia Avanzada de Logística, Liderazgo de Equipos, Costos y Presupuestos, Cobertura Universal en Salud, Gerencia en Empresas Familiares

**Ciclo 4:** Derecho Médico y Bioética, Comunicación/Media Training, Finanzas Corporativas, Auditoría en Salud, Negociaciones

**Ciclo 5:** Gerencia Comercial, Gerencia del Riesgo I, Balanced Scorecard, Gerencia Social, Evaluación Económica de Proyectos, Emprendimiento, Tesis I

**Ciclo 6:** Dirección Estratégica de Marketing, Gerencia de Proyectos, Sociedades y Tributación, Dirección Estratégica de Empresas, Simulador de Vuelo Gerencial, Gerencia del Riesgo II, Tesis II

## Flujo del Sistema

```
PDF_Ciclos/*.pdf → pdf_reader (37 cursos)
    → db.registrar_cursos (SQLite)
    → browser (Chrome perfil "Diseñador" / Profile 4)
    → navegar a aulavirtual.upc.edu.pe
    → por cada curso pendiente:
        → navigator.buscar_curso (match directo → AI fallback)
        → navigator.extraer_enlaces (selectores → AI fallback)
        → ai_helper.clasificar_enlace (reglas → GPT fallback)
        → downloader (E:\RPA_Descargas\Ciclo X\CURSO\archivo)
        → db.registrar_descarga
    → reporte final
```

---

## Requisitos Previos

| Requisito | Detalle |
|-----------|---------|
| Python | 3.11+ |
| Google Chrome | Instalado, perfil "Diseñador" con sesión activa en la plataforma |
| Windows | 10/11 |
| Disco E: | Con espacio disponible |
| API key OpenAI | Para GPT-4o-mini (uso mínimo) |

---

## Paso 1: Clonar e instalar

```bash
git clone <URL_DEL_REPO> RPA_UPC
cd RPA_UPC
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Paso 2: Configurar API key

Crear archivo `.env` en la raíz (copiar de `.env.example`):

```
OPENAI_API_KEY=sk-tu-api-key-aqui
```

> Se usa `gpt-4o-mini` para minimizar costos. Solo se llama cuando las reglas locales no son suficientes.

## Paso 3: Verificar sesión en Chrome

La configuración ya apunta al perfil correcto:
- **Perfil:** Diseñador = `Profile 4`
- **Ruta:** `C:\Users\Master PC\AppData\Local\Google\Chrome\User Data`

**Antes de ejecutar:**
1. Abre Chrome con el perfil "Diseñador"
2. Navega a `aulavirtual.upc.edu.pe` y verifica que estás logueado
3. **Cierra TODAS las ventanas de Chrome**

## Paso 4: Ejecutar

```bash
# Procesar todos los cursos pendientes
python main.py

# Solo un ciclo
python main.py --ciclo 3

# Ver reporte
python main.py --reporte

# Listar cursos detectados
python main.py --listar

# Reiniciar cursos con error
python main.py --reset
```

---

## Estructura de descargas en disco E:

```
E:\RPA_Descargas\
├── Ciclo 1\
│   ├── ETICA Y RESPONSABILIDAD SOCIAL\
│   │   ├── Clase_01.mp4
│   │   └── Presentacion.pptx
│   ├── CONTABILIDAD GERENCIAL\
│   └── ...
├── Ciclo 2\
│   └── ...
├── Ciclo 3\
├── Ciclo 4\
├── Ciclo 5\
└── Ciclo 6\
```

---

## Uso de AI (GPT) — Diseñado para mínimo consumo de tokens

| Situación | ¿Usa GPT? | Costo aprox. |
|-----------|-----------|--------------|
| Match exacto de curso por nombre | NO | $0 |
| Match parcial (contiene nombre) | NO | $0 |
| No hay match → busca entre opciones | SI (gpt-4o-mini) | ~$0.001 |
| Enlace con extensión conocida (.mp4, .pdf) | NO | $0 |
| Enlace de navegación/actividad | NO | $0 |
| Enlace ambiguo sin clasificar | SI | ~$0.001 |
| Buscar videos en HTML sin selectores | SI (HTML recortado 2KB) | ~$0.002 |

**Estimación total:** ~$0.05-0.20 por ejecución completa (37 cursos).

---

## Base de Datos SQLite (`registro.db`)

**cursos:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | PK |
| nombre | TEXT | Nombre del curso |
| ciclo | TEXT | "Ciclo 1" ... "Ciclo 6" |
| estado | TEXT | pendiente / en_proceso / completado / error / sin_contenido |
| fecha_inicio | TEXT | Timestamp |
| fecha_fin | TEXT | Timestamp |
| error | TEXT | Mensaje de error |

**descargas:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | PK |
| curso_id | INTEGER | FK a cursos |
| url | TEXT | URL de origen (UNIQUE con curso_id) |
| archivo | TEXT | Ruta en disco E: |
| tipo | TEXT | video, documento, grabación |
| fecha | TEXT | Timestamp |

---

## Personalización de Selectores (después del primer run)

Los selectores en `navigator.py` están marcados con `[AJUSTAR]`.
La plataforma UPC usa **Blackboard Learn**. Después del primer intento:

1. Abre Chrome con perfil Diseñador
2. Ve a `aulavirtual.upc.edu.pe`
3. F12 → Inspeccionar:
   - Campo de búsqueda
   - Enlaces a cursos
   - Secciones de contenido/recursos/grabaciones
4. Actualiza selectores en `navigator.py`

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "No se pudo abrir el navegador" | Cierra TODAS las ventanas de Chrome (Task Manager si es necesario) |
| "Sin sesión activa" | Abre Chrome Diseñador → login manual → cierra → ejecuta |
| "Curso no encontrado" | Ajusta selectores; verifica nombre en plataforma |
| Descarga falla | Verifica espacio en E: y permisos |
| API key error | Verifica `.env` con `OPENAI_API_KEY=sk-...` |
| Timeout | Aumenta `TIMEOUT_NAVEGACION` en `config.py` |

---

## Seguridad

- **No compartir** `registro.db` (puede contener URLs con tokens de sesión)
- **No subir** `.env` a git (ya está en .gitignore)
- Las credenciales de la plataforma se manejan via el perfil de Chrome
- La API key de OpenAI solo se usa localmente
