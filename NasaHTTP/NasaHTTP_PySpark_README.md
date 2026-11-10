# 🚀 Análisis de Logs de Servidores NASA con PySpark

Pipeline de **Ingeniería de Datos** que convierte el log HTTP crudo de los servidores de la
NASA (agosto de 1995) en reportes de seguridad, rendimiento y contenido usando **PySpark**.

Los logs son el ejemplo canónico de dato *no estructurado*: texto plano con un formato
semiestructurado que se rompe en cuanto aparece una línea rara. Este proyecto muestra cómo
parsearlo de forma robusta, limpiarlo y explotarlo a escala con procesamiento distribuido.

---

## 📦 El dataset

| | |
|---|---|
| **Fichero** | `access.log` (Common Log Format ampliado) |
| **Origen** | NASA Kennedy Space Center HTTP logs, agosto 1995 |
| **Tamaño** | 167.8 MB |
| **Líneas** | 1,569,898 |
| **Periodo** | 01/Aug/1995 – 31/Aug/1995 |

Cada línea tiene esta forma:

```
in24.inetnebr.com - - [01/Aug/1995:00:00:01 -0400] "GET /shuttle/missions/sts-68/news/sts-68-mcc-05.txt HTTP/1.0" 200 1839
└── IP ─────────┘     └── timestamp ──────────────┘ └─ método ─┘ └── endpoint ──────────────────────────────────┘ └proto┘ └status┘ └─ bytes ─┘
```

> El dataset **no se redistribuye** en este repo (no es libre). Colócalo en `data/access.log`
> — ver [Cómo ejecutar](#-cómo-ejecutar).

---

## 🗂️ Estructura del proyecto

```
NasaHTTP/
├── src/
│   ├── nasa_logs.py             # Patrón regex + parsing en Python puro (fuente de verdad)
│   └── nasa_logs_pipeline.py    # Pipeline PySpark: ingesta -> análisis -> 4 CSV
├── tests/
│   ├── test_parsing.py          # Pruebas del regex (pytest, sin Spark ni Docker)
│   └── test_pipeline_integration.py  # Ejecuta el pipeline y valida el CSV (requiere Spark)
├── winutils/bin/                # winutils.exe + hadoop.dll (requisito de Spark en Windows)
├── data/access.log              # Dataset (gitignored, ~168 MB)
├── output/                      # Reportes generados (gitignored)
├── NasaHTTP_PySpark.ipynb       # Notebook para exploración interactiva (reutiliza src/)
├── requirements.txt
└── NasaHTTP_PySpark_README.md
```

---

## 🛠️ Requisitos

| Componente | Versión | Nota |
|---|---|---|
| Python | 3.9 – 3.12 | Probado con 3.11 |
| PySpark | 3.5.3 | `pip install -r requirements.txt` |
| Java (JDK) | 8 / 11 / 17 (21 funciona) | Spark 3.5 soporta oficialmente hasta Java 17 |
| `winutils.exe` + `hadoop.dll` | Hadoop 3.3.x | **Solo Windows** — ya incluidos en `winutils/bin/` |

> **Windows:** Hadoop necesita `winutils.exe` o Spark aborta con
> `HADOOP_HOME and hadoop.home.dir are unset`. Los binarios están en `winutils/bin/` y el
> pipeline configura `HADOOP_HOME` automáticamente. Si los borras, vuelve a descargarlos de
> [cdarlint/winutils](https://github.com/cdarlint/winutils) (rama `hadoop-3.3.6`).

---

## ▶️ Cómo ejecutar

### 1. Entorno

```bash
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt      # Windows
# source venv/bin/activate && pip install -r requirements.txt   # Linux/macOS
```

### 2. Dataset

Coloca el `access.log` en `data/access.log`. También puedes indicar la ruta de otras formas:

```bash
python src/nasa_logs_pipeline.py --log "D:/ruta/a/access.log"    # argumento
set NASA_LOG_PATH=D:/ruta/a/access.log                           # variable de entorno
```

### 3. Pipeline

```bash
python src/nasa_logs_pipeline.py                 # ejecución completa (~5 min)
python src/nasa_logs_pipeline.py --sample 200000 # prueba rápida con 200k líneas
python src/nasa_logs_pipeline.py --no-plot       # sin generar la gráfica
python src/nasa_logs_pipeline.py --output-dir /tmp/salida   # otra carpeta de salida
```

### 4. Pruebas

```bash
python -m pytest tests/ -v                      # todo (20 pruebas, ~1 min)
python -m pytest tests/test_parsing.py -v       # solo el regex (0.1 s, sin Spark)
```

- `test_parsing.py` valida el regex con Python puro: no necesita Spark, Java ni Docker. Cubre los
  casos límite del log real (sin protocolo, espacios dobles, tamaños `-`, líneas corruptas) y
  verifica el contrato con el README.
- `test_pipeline_integration.py` **ejecuta el pipeline de verdad** sobre un log sintético y comprueba
  que los CSV generados se pueden releer con pandas. Es la prueba que protege contra el bug de
  escapado de comillas; se salta solo si PySpark no está instalado.

---

## 📈 Salidas (`output/`)

| Fichero | Contenido |
|---|---|
| `nasa_logs_estructurados_FULL.csv` | Dataset completo parseado y limpio, listo para BI (~157 MB) |
| `reporte_seguridad_ips.csv` | Top 100 IPs por errores: `ip`, `errores`, `total_peticiones`, `tasa_error_pct` |
| `reporte_trafico_hora.csv` | Peticiones e IPs distintas por hora del día (24 filas) |
| `reporte_paginas_visitadas.csv` | Top 100 recursos: `endpoint`, `peticiones`, `ips_distintas` |
| `trafico_por_hora.png` | Gráfica de peticiones por hora |

---

## 🔍 Hallazgos

Cifras medidas sobre las 1,569,898 líneas del log:

- **10,225 peticiones con error** (`status >= 400`), un **0.65 %** del total. El código
  dominante es `404` (10,020), seguido de `403` (171), `501` (27), `400` (4) y `500` (3).
- **Las IPs más "agresivas" son bots de indexación, no atacantes.** `dialip-217.den.mmc.com`
  (62 errores sobre 111 peticiones, un **55.9 %**) y `piweba3y.prodigy.com` (47 errores)
  piden rutas que no existen de forma sistemática: son crawlers recorriendo enlaces rotos.
  Nueve IPs del top 100 tienen **100 % de tasa de error** (`ts8-1.westwood.ts.ucla.edu`,
  `203.13.168.17`, `onramp2-9.onr.com`, `198.40.25.102.sap2.artic.edu`, `msp1-16.nas.mr.net`…),
  señal típica de un scraper siguiendo un índice obsoleto.
- **Los recursos más pedidos no son páginas, son imágenes.** El top 5 son logotipos
  (`/images/NASA-logosmall.gif` con 97,392 peticiones desde 41,067 IPs distintas). Son assets
  incrustados en cada página, así que su volumen refleja el tráfico de las páginas, no su
  popularidad individual.
- **El tráfico es diurno y muy marcado.** El pico está a las **15:00** (109,427 peticiones) y
  el valle a las **04:00** (26,722): una relación de **4.1×** coherente con el huso horario de
  EE. UU., ya que el log registra en `-0400`.
- **`GET` domina absolutamente**: 1,565,093 peticiones frente a 3,965 `HEAD` y 111 `POST`.
  El servidor era esencialmente de lectura estática.
- **Hay rastro de sondeos de exploits.** 10 líneas del log no son peticiones HTTP válidas sino
  **bytes binarios** enviados al puerto (p. ej. `"\xfd\xd1\xed.\x8a\x0b2..."` desde
  `128.159.117.22`). El servidor respondió `400` a todas: son escaneos rechazados. Se
  conservan en el dataset (el 400 es información de seguridad) con `method = UNKNOWN`.

---

## 🧩 Desafíos técnicos (bugs reales encontrados y corregidos)

Esta sección documenta los fallos que **no se ven leyendo el código**: el script corría sin
error y producía resultados plausiblemente erróneos.

### 1. El regex descartaba ~1,800 peticiones válidas en silencio

**Síntoma:** el pipeline decía "1,568,099 registros procesados" y nadie notaba que faltaban
1,799 líneas.

**Causa raíz:** el patrón original exigía tres campos separados por espacios dentro de las
comillas:

```
"(.*?) (.*?) (.*?)"     -> método, endpoint, protocolo
```

Pero el log real contiene peticiones **sin protocolo** (`"GET /ruta"`) y con **espacios
dobles** (`"GET /ruta   HTTP/1.0"`). Ambas cosas rompen el patrón y la línea se descarta sin
avisar.

**Arreglo:** protocolo opcional + `\s+` en lugar de espacio literal:

```python
LOG_PATTERN = r'^(\S+) - - \[(.*?)\] "(\S+)\s+(\S+?)(?:\s+(\S+))?\s*"\s+(\d{3})\s+(\d+|-)'
```

| Patrón | Registros parseados | Líneas descartadas |
|---|---|---|
| Original | 1,568,099 | 1,799 (0.115 %) |
| Corregido | **1,569,173** | **725 (0.046 %)** — sólo corrupción genuina |

**Verificación:** `tests/test_parsing.py` fija ambos casos límite como casos de prueba.

### 2. `content_size` se quedaba como texto

El grupo del tamaño es `(\d+|-)`. El código original lo dejaba como `string`, así que
`"-"` (el servidor no reporta tamaño) se mezclaba con los números y cualquier suma o media
habría fallado. **Arreglo:** `.cast("int")` — con `spark.sql.ansi.enabled=false`, `"-"` pasa a
`NULL` en vez de reventar.

### 3. El README prometía ficheros que el código no generaba

El README listaba `reporte_trafico_hora.csv` y `reporte_paginas_visitadas.csv`. El notebook
escribía `reporte_horas.csv` y **nunca generaba el reporte de páginas**. Un reclutador que
siguiera el README no encontraba los ficheros. **Arreglo:** el nombre de cada salida vive en un
único diccionario (`OUTPUT_FILES`) que el README y una prueba de contrato verifican.

### 4. Ruta del dataset hardcodeada a una carpeta inexistente

El notebook apuntaba a `C:\Users\junio\Documents\Datacamp PySpark\Datasets\access.log`, pero el
fichero estaba un nivel más abajo (`Documents\Datacamp\Datacamp PySpark\...`). El notebook no
arrancaba. **Arreglo:** resolución en cascada `--log` → `NASA_LOG_PATH` → `data/access.log`,
con un mensaje de error que indica qué rutas se comprobaron.

### 5. `SPARK_HOME` huérfano rompía el arranque de Spark

**Síntoma:** `FileNotFoundError: [WinError 2] The system cannot find the file specified` al
crear la `SparkSession`, sin más pistas.

**Causa raíz:** el sistema tenía `SPARK_HOME=C:\spark-4.1.1-bin-hadoop3` y esa carpeta **ya no
existía** (quedó de una instalación anterior). PySpark respeta `SPARK_HOME` y buscaba ahí su
`spark-submit.cmd`. Además, `/c/spark-4.1.1-bin-hadoop3/bin` seguía colgando del `PATH`.

**Arreglo:** el pipeline fuerza `SPARK_HOME` al Spark **empaquetado dentro del propio paquete
`pyspark`** del venv, lo que además garantiza que la versión de Spark y la de PySpark casan.

### 6. Hadoop en Windows exige `winutils.exe`

Spark abortaba con `HADOOP_HOME and hadoop.home.dir are unset` al inicializar su
`ShutdownHookManager`, **antes incluso de leer el fichero**. En Windows, Hadoop necesita
`winutils.exe` y `hadoop.dll`. **Arreglo:** binarios incluidos en `winutils/bin/` y
`HADOOP_HOME` + `PATH` configurados automáticamente por el pipeline.

### 7. Volcar 1.5M filas al driver con `toPandas()`

El notebook hacía `structured_logs.toPandas()` para exportar el CSV completo: 1.5M filas
serializadas al driver de golpe. **Arreglo:** escritura distribuida con
`coalesce(1).write.csv()` y renombrado del `part-*.csv` al nombre final, de modo que el
resultado sigue siendo **un solo fichero** con el nombre que promete el README.

### 8. El CSV generado no se podía abrir con pandas ni Excel

**Síntoma:** el pipeline terminaba en verde y `nasa_logs_estructurados_FULL.csv` parecía
perfecto… hasta que lo abrías:

```
pandas.errors.ParserError: Error tokenizing data.
C error: Expected 7 fields in line 275355, saw 8
```

**Causa raíz:** tres líneas del log tienen una **comilla de más** en la petición
(`"GET /ksc.html" HTTP/1.0" 404 -`), así que el endpoint capturado acaba en `"`. Al escribir
el CSV, Spark usa por defecto `escape = \`, es decir escapa la comilla como `\"` **en lugar de
duplicarla** (`""`). Eso no es RFC 4180: el parser no cierra el campo, se traga las filas
siguientes y revienta. Con `csv.reader` el fichero perdía 370 registros de esa forma.

**Arreglo:**

```python
.option("quote", '"').option("escape", '"')   # comillas duplicadas = CSV estándar
```

Y, para que no vuelva a pasar en silencio, el pipeline **relee el CSV** con pandas por chunks
y compara el número de filas con el del DataFrame antes de darlo por bueno:

```
verificación CSV: 1,569,173 filas legibles (esperadas 1,569,173) -> OK
```

**Lección:** "el fichero se ha escrito sin error" no significa "el fichero es legible".

---

## ⚠️ Limitaciones conocidas

- **725 líneas (0.046 %) no se parsean** y se descartan: son corrupción real del fichero
  (comillas extra, espacios literales dentro de la URL, códigos de estado truncados). No se
  intenta "adivinar" su contenido; el pipeline reporta cuántas descarta.
- **El log no es UTF-8.** 10 líneas contienen bytes fuera de UTF-8 (los sondeos binarios).
  `spark.read.text` no permite fijar la codificación (la opción `encoding` se ignora), así que
  esos bytes se decodifican como `U+FFFD` y los endpoints de esas 10 líneas salen con caracteres
  de reemplazo. Afecta al 0.0006 % del dataset y se ha preferido **documentarlo antes que
  ocultarlo**; la alternativa sería leer el fichero como `binaryFile` y decodificar en Latin-1.
- **`tasa_error_pct` no es comparable entre IPs con poco tráfico.** Una IP con 1 petición y 1
  error da 100 %, igual que un bot con 37 errores sobre 37. Hay que leerlo junto a
  `total_peticiones`.
- **La extracción de la hora asume el huso del log (`-0400`)**; no se normaliza a UTC.
- El notebook (`NasaHTTP_PySpark.ipynb`) se mantiene por valor didáctico, pero **la vía
  reproducible es el script** `src/nasa_logs_pipeline.py`.

---

## 🧠 Qué demuestra este proyecto

- **Parsing robusto de datos no estructurados**: regex con casos límite cubiertos por tests,
  y conciencia de que descartar filas en silencio es un bug, no una limpieza.
- **Diagnóstico de entorno**: los tres fallos de arranque (`SPARK_HOME`, `HADOOP_HOME`,
  `JAVA_HOME`) son errores clásicos de Spark en Windows y aquí están resueltos y documentados.
- **Contrato código ↔ documentación**: los nombres de salida viven en un único sitio y una
  prueba verifica que el README los respeta.
- **Escritura escalable y verificada**: exportar 1.5M filas sin volcar el dataset al driver, y
  releer el CSV generado para confirmar que es realmente legible.
