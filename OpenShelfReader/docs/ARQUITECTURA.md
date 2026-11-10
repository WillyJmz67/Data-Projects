# Arquitectura — OpenShelf Reader

## 1. Visión general

MVVM + Clean Architecture simplificada, en un único módulo Gradle (`app`) organizado por capas en paquetes. Se evita Hilt para reducir la fricción inicial: un `AppContainer` manual provee las dependencias.

```text
UI (Compose, ViewModels)
        ↓  llama a
LibraryRepository (repositorio de dominio/datos)
        ↓  usa
DAOs (Room)   +   Servicios de red (OkHttp)   +   Almacenamiento de archivos
```

## 2. Estructura de paquetes

```text
org.openshelf.reader/
├── OpenShelfApp.kt                  # Application: crea el AppContainer
├── MainActivity.kt                 # Activity principal + navegación inferior
├── di/
│   └── AppContainer.kt             # Contenedor de dependencias manual
├── domain/
│   └── model/                       # Modelos puros de dominio (sin Android)
│       ├── Book.kt
│       ├── BookFormat.kt
│       ├── RemoteCatalog.kt        # RemoteCatalog + RemoteBook (serializables)
│       └── RepoSource.kt           # Origen GitHub (construye URLs de raw)
├── data/
│   ├── db/
│   │   ├── OpenShelfDatabase.kt    # RoomDatabase (versión 1)
│   │   ├── entity/                 # BookEntity, ReadingProgressEntity, RepoSourceEntity
│   │   └── dao/                    # BookDao, ProgressDao, RepoSourceDao
│   ├── network/
│   │   ├── GitHubCatalogRepository.kt  # Descarga y parsea catalog.json
│   │   └── DownloadService.kt           # Descarga archivos a almacenamiento interno
│   ├── repository/
│   │   └── LibraryRepository.kt    # Fachada única para la UI
│   └── worker/
│       └── BookDownloadWorker.kt   # Descargas en segundo plano (WorkManager)
├── epub/
│   ├── EpubModels.kt               # EpubManifest, EpubChapter, EpubTocItem
│   └── EpubParser.kt               # container.xml → OPF → spine/NCX (XmlPullParser)
├── util/
│   └── NaturalOrder.kt              # Orden natural para páginas de cómic
└── ui/
    ├── theme/                      # Material 3 + dynamic color
    ├── navigation/                 # Screen (rutas) + OpenShelfNavHost
    ├── components/                 # BookCover, ZoomableBitmap
    ├── library/                    # Biblioteca + ViewModel
    ├── repositories/               # Repos GitHub + ViewModel
    ├── catalog/                    # Catálogo remoto + ViewModel
    ├── settings/                   # Ajustes
    ├── reader/                     # ReaderActivity (despacho por formato)
    ├── epub/                       # EpubReaderScreen (WebView)
    ├── pdf/                        # PdfReaderScreen (PdfRenderer)
    └── cbz/                        # CbzReaderScreen (ZipFile)
```

## 3. Flujo de datos

### 3.1 Añadir repositorio y descargar un libro
```text
RepositoriesScreen
  → RepositoriesViewModel.addRepo("usuario/repo")
    → LibraryRepository.addRepo()
      → RepoSourceDao.upsert(RepoSourceEntity)

RemoteCatalogScreen(repoId)
  → RemoteCatalogViewModel.load(repoId)
    → LibraryRepository.findRepoById() + fetchCatalog()
      → GitHubCatalogRepository (OkHttp) → catalog.json
  → usuario pulsa "Descargar"
    → RemoteCatalogViewModel.download()
      → LibraryRepository.downloadRemoteBook()
        → DownloadService.downloadFile() (libro y portada → filesDir/books, filesDir/covers)
        → BookDao.upsert(BookEntity)
```

También existe `BookDownloadWorker` (WorkManager) para encolar descargas en segundo plano desde la UI sin bloquear.

### 3.2 Leer y guardar progreso
```text
LibraryScreen (clic en libro)
  → ReaderActivity(book_id, book_path)
    → ReaderRoot: BookFormat.fromFileName() decide EPUB / PDF / CBZ
      → Lector correspondiente:
        - Lee progreso: LibraryRepository.getProgress()
        - Al navegar: LibraryRepository.saveProgress(location, percent)
          → ProgressDao.upsert + BookDao.update (percent, lastReadAt)
```

### 3.3 Códigos de ubicación del progreso
| Formato | location | Ejemplo |
|---|---|---|
| EPUB | `epub:chapter=N` | `epub:chapter=3` |
| PDF | `pdf:page=N` | `pdf:page=42` |
| CBZ | `cbz:page=N;rtl=B;double=B` | `cbz:page=10;rtl=true;double=false` |

## 4. Decisiones técnicas clave

- **Room + Flow**: los DAOs exponen `Flow` para que la UI se actualice en tiempo real (biblioteca reactiva).
- **AppContainer manual**: suficiente para el MVP; migrar a Hilt si el proyecto crece.
- **EPUB en WebView**: renderizado simple y fiable de HTML/XHTML local; JavaScript solo se habilita para aplicar el tema oscuro (inversión CSS) sobre archivos locales.
- **PDF con PdfRenderer** (API del sistema): sin dependencias nativas pesadas; acceso serializado con Mutex porque PdfRenderer no es thread-safe.
- **CBZ con ZipFile**: acceso por entrada sin descomprimir todo; `inSampleSize` para decodificar páginas grandes sin desbordar memoria.
- **raw.githubusercontent.com** en vez de la API REST de GitHub: sin límites de rate ni tokens para repos públicos.
- **GPL-3.0**: obliga a mantener abiertas las versiones distribuidas.

## 5. Puntos de extensión (fase 2+)

- **Nuevo formato**: añadir entrada en `BookFormat`, rama en `ReaderRoot` y un paquete `ui/<formato>`.
- **Notas/resaltados**: nueva entidad Room + DAO + pantalla.
- **Importación local SAF**: `ACTION_OPEN_DOCUMENT` en la biblioteca y copia a `filesDir/books`.
- **Actualizador interno**: consultar `https://api.github.com/repos/<owner>/<repo>/releases/latest`.
- **Modularización Gradle**: extraer `core-model`, `core-database`, `core-network`, `feature-*` cuando el monolito crezca.
