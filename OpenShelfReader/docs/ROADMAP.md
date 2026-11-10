# Roadmap — OpenShelf Reader

## Estado: Fase 1 (MVP) ✅ completada

| Fase | Contenido | Estado |
|---|---|---|
| Fase 1 — Base | Proyecto Android, Kotlin + Compose + Material 3, Room, navegación | ✅ |
| Fase 2 — Biblioteca local | Base de datos, entidades, DAOs, repositorio, pantalla de biblioteca | ✅ |
| Fase 3 — Descarga desde GitHub | Añadir repos, catalog.json, descarga de libros, guardado en biblioteca | ✅ |
| Fase 4 — Lector CBZ | ZIP, orden natural, zoom, RTL manga, doble página, recordar página | ✅ |
| Fase 5 — Lector PDF | PdfRenderer, paginado, zoom, recordar página | ✅ |
| Fase 6 — Lector EPUB | container.xml/OPF/spine, WebView, TOC NCX, modo oscuro, progreso | ✅ |
| Fase 7 — Distribución | GitHub Actions, APK firmado, Releases con checksum | ✅ |

## Pendiente — orden recomendado

### Fase 8 — Actualizador interno + mejoras de biblioteca
- [ ] Comprobar nuevas versiones vía `https://api.github.com/repos/<owner>/<repo>/releases/latest`.
- [ ] Diálogo de actualización + descarga del APK + abrir instalador.
- [ ] «Continuar leyendo» en la pantalla de inicio.
- [ ] Mostrar progreso sobre la portada.
- [ ] Favoritos y colecciones (el campo `isFavorite` ya existe en la BD).
- [ ] Búsqueda en la biblioteca.
- [ ] Importar libros locales con Storage Access Framework (ACTION_OPEN_DOCUMENT) y copiarlos a `filesDir/books`.
- [ ] Usar el `readingDirection` del catálogo para activar RTL automáticamente en manga.

### Fase 9 — Nuevos formatos
- [ ] CBR (RAR) — evaluar librería (junrar / commons-compress) y licencias.
- [ ] CB7 (7-Zip).
- [ ] TXT con paginado.
- [ ] Carpetas de imágenes sueltas como «cómics».

### Fase 10 — Lectura avanzada
- [ ] EPUB: ajustes de fuente, tamaño, interlineado, márgenes, justificado.
- [ ] EPUB fixed-layout.
- [ ] PDF: modo oscuro, recorte de márgenes, renderizado progresivo de páginas grandes.
- [ ] CBZ: recorte automático de márgenes blancos, precarga de páginas adyacentes, pasar página con botón de volumen, zonas de toque configurables.
- [ ] Marcadores y continuar desde marcador.

### Fase 11 — Anotaciones y utilidades
- [ ] Notas y resaltados persistentes (nueva tabla Room).
- [ ] Búsqueda de texto dentro del libro.
- [ ] Texto a voz (TTS del sistema) para EPUB.
- [ ] Exportar notas.
- [ ] Estadísticas de lectura.
- [ ] Backup local (JSON) de biblioteca y progreso.

### Fase 12 — Infraestructura
- [ ] Tests unitarios del parser EPUB y del orden natural CBZ.
- [ ] Modularización Gradle (core-model, core-database, core-network, feature-*).
- [ ] Migrar el contenedor manual a Hilt.
- [ ] F-Droid: receta de build y metadatos.

## Limitaciones conocidas de la fase 1

| Lector | Limitaciones |
|---|---|
| EPUB | Modo oscuro por inversión de colores (imágenes también se invierten); JS solo para el tema; fixed-layout no optimizado; TOC solo desde NCX (sin nav de EPUB 3) |
| PDF | Sin selección de texto ni búsqueda ni anotaciones; PDFs escaneados son solo imágenes; PDFs muy grandes pueden consumir memoria |
| CBZ | Solo CBZ; doble página básica; sin recorte de márgenes; sin precarga |
| General | Sin importación local aún (solo descargas); sin favoritos visibles; sin búsqueda |
