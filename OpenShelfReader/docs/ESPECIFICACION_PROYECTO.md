# Especificación del proyecto — OpenShelf Reader

## 1. Resumen

**OpenShelf Reader** es una aplicación Android de código abierto para leer eBooks, cómics y manga. Se distribuye gratuitamente como APK mediante GitHub Releases (sin Google Play). Su biblioteca puede alimentarse desde repositorios públicos de GitHub mediante un catálogo `catalog.json`.

## 2. Decisiones de producto confirmadas

| Área | Decisión |
|---|---|
| Plataforma | Android nativo |
| Lenguaje | Kotlin |
| UI | Jetpack Compose + Material 3 |
| Android mínimo | Android 8.0 / API 26 |
| Android objetivo | API 34 |
| Arquitectura | MVVM + Clean Architecture simplificada (monolito organizado por paquetes) |
| Base de datos local | Room |
| Preferencias | DataStore (reservado para ajustes futuros) |
| Descargas | OkHttp + WorkManager |
| Imágenes | Coil |
| Serialización | Kotlinx Serialization |
| Conectividad GitHub | raw.githubusercontent.com (catalog.json + archivos) |
| Publicidad | No |
| Analíticas / trackers | No |
| Cuenta de usuario | No |
| Sincronización entre dispositivos | No |
| Progreso de lectura | Sí, local (por libro) |
| Formatos MVP | EPUB, PDF, CBZ |
| Formatos fase 2 | CBR, CB7, imágenes sueltas, TXT |
| DRM | No soportado |
| Licencia | GPL-3.0 |
| Idiomas iniciales | Español e inglés |
| Distribución | GitHub Releases (APK firmado) |

## 3. Alcance funcional (MVP)

### 3.1 Biblioteca local
- Lista de libros descargados con portada, título y autor.
- Orden: últimos leídos primero (`lastReadAt DESC, addedAt DESC`).
- Progreso de lectura visible y persistente.
- Borrado de libros (elimina archivo y portada del almacenamiento).

### 3.2 Repositorios GitHub
- Añadir repositorio público con `usuario/repositorio` o URL completa (con o sin rama).
- Persistencia local de los repositorios añadidos.
- Eliminar repositorio.

### 3.3 Catálogo remoto
- Descarga y parseo de `catalog.json` desde `raw.githubusercontent.com`.
- Lista de libros con título, autor y botón de descarga.
- Descarga del libro (y su portada si existe) al almacenamiento interno privado.
- Registro automático del libro en la biblioteca.

### 3.4 Lectores
| Formato | Implementación | Funciones |
|---|---|---|
| EPUB | Parser propio (container.xml → OPF → spine/NCX) + WebView | Capítulos, TOC (NCX), modo oscuro por inversión CSS, progreso por capítulo |
| PDF | `PdfRenderer` + `HorizontalPager` | Paginado, zoom, progreso por página |
| CBZ | `ZipFile` + `BitmapFactory` + `HorizontalPager` | Orden natural de páginas, RTL manga, doble página, zoom, progreso por página |

### 3.5 Progreso de lectura
- Tabla `reading_progress` (ubicación + porcentaje + timestamp).
- Códigos de ubicación: `epub:chapter=N`, `pdf:page=N`, `cbz:page=N;rtl=BOOL;double=BOOL`.
- Al reabrir un libro, el lector salta a la última posición guardada.

## 4. Modelo de datos

### Book (dominio)
```kotlin
data class Book(
    id, title, author, format, localPath, remoteUrl, coverPath,
    collection, language, repoId, addedAt, lastReadAt,
    progressPercent, isFavorite
)
```

### Entidades Room
- `BookEntity` — tabla `books`
- `ReadingProgressEntity` — tabla `reading_progress`
- `RepoSourceEntity` — tabla `repo_sources`

### Fuentes remotas
```kotlin
RepoSource.catalogUrl  ->  https://raw.githubusercontent.com/{owner}/{repo}/{branch}/catalog.json
RepoSource.resolveFileUrl(path)  ->  .../{branch}/{path}
```

## 5. Permisos

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

Solo dos permisos. Sin acceso global al almacenamiento: los libros viven en el almacenamiento interno privado de la app. Para abrir archivos locales del usuario se usará Storage Access Framework (fase 2).

## 6. Restricciones legales y de contenido

- La app **no soporta DRM** ni lo elude.
- Solo descarga de **repositorios públicos** de GitHub (sin tokens, sin cuentas).
- Los repositorios de libros deben contener contenido legal, de dominio público o del que el usuario tenga derechos.
- Límites de GitHub a tener en cuenta: archivos de hasta 100 MB por archivo en repos; para archivos mayores usar GitHub Releases en el repo de libros.

## 7. Fuera de alcance (fase 1)

- Sincronización entre dispositivos.
- Notas, resaltados, búsqueda en el texto.
- Texto a voz (TTS).
- CBR/CB7/TXT.
- OPDS, integración Calibre.
- Actualizador interno de la app.

Estas funciones están planificadas en `docs/ROADMAP.md`.
