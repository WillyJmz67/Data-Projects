# OpenShelf Reader

**OpenShelf Reader** es una aplicación Android gratuita y de código abierto para leer eBooks, cómics y manga.

No requiere cuenta, no incluye publicidad, no usa trackers y no sincroniza datos con servidores externos.

> ⚠️ Esta aplicación no soporta DRM ni está pensada para eludir protecciones. Debe usarse únicamente con contenido legal, de dominio público o que tengas derecho a leer y descargar.

## Características

- Lectura local de libros.
- Biblioteca con portadas y progreso de lectura.
- Soporte inicial para:
  - EPUB
  - PDF
  - CBZ (cómics y manga)
- Descarga de libros desde repositorios públicos de GitHub.
- Modo manga derecha a izquierda (RTL) y doble página.
- Modo claro/oscuro (Material You en Android 12+).
- Sin cuenta de usuario.
- Sin anuncios.
- Sin trackers.
- Sin sincronización en la nube.
- Progreso guardado localmente.

## Formatos soportados

| Formato | Estado |
|---|---|
| EPUB | Soporte básico |
| PDF | Soporte básico |
| CBZ | Soporte básico |
| CBR | Planeado |
| CB7 | Planeado |
| TXT | Planeado |

## Instalación

1. Ve a la sección [Releases](../../releases).
2. Descarga el archivo `OpenShelfReader-VERSION.apk`.
3. Instálalo en tu dispositivo Android (Android 8.0 / API 26 o superior).
4. Si Android muestra una advertencia, permite la instalación desde fuentes desconocidas.

> Recomendación: instala solo los APK publicados en el repositorio oficial de este proyecto. Cada release incluye un checksum `.sha256` para verificar la integridad del archivo.

## Añadir un repositorio de libros

OpenShelf Reader puede descargar libros desde repositorios públicos de GitHub.

El repositorio debe tener un archivo `catalog.json` en la raíz. Estructura recomendada:

```text
mi-biblioteca/
├── catalog.json
├── covers/
│   ├── libro1.jpg
│   └── manga1.jpg
└── books/
    ├── libro1.epub
    ├── libro2.pdf
    └── manga1.cbz
```

Ejemplo de `catalog.json`:

```json
{
  "name": "Mi biblioteca",
  "description": "Biblioteca pública de ejemplo",
  "books": [
    {
      "id": "libro1",
      "title": "Libro de ejemplo",
      "author": "Autor de ejemplo",
      "file": "books/libro1.epub",
      "cover": "covers/libro1.jpg",
      "type": "epub",
      "collection": "Clásicos",
      "language": "es"
    },
    {
      "id": "manga1",
      "title": "Manga de ejemplo",
      "author": "Autor del manga",
      "file": "books/manga1.cbz",
      "cover": "covers/manga1.jpg",
      "type": "cbz",
      "collection": "Manga",
      "language": "es",
      "readingDirection": "rtl"
    }
  ]
}
```

Consulta [`docs/README_REPO_LIBROS.md`](docs/README_REPO_LIBROS.md) para la especificación completa del catálogo.

## Uso

1. Abre la app.
2. Ve a la pestaña **Repositorios**.
3. Añade un repositorio público de GitHub (`usuario/repositorio` o la URL completa).
4. Entra en el catálogo y descarga los libros que quieras.
5. Los libros aparecerán en tu **Biblioteca**, listos para leer.

## Privacidad

OpenShelf Reader no recopila datos personales.

La aplicación puede conectarse a Internet únicamente para:

- Descargar catálogos (`catalog.json`) desde repositorios de GitHub que tú añadas.
- Descargar los libros que elijas manualmente.

No se usa publicidad, analítica ni seguimiento.

## Construir desde el código fuente

Requisitos:

- Java 17 (JDK)
- Android SDK (API 34) — lo instala Android Studio
- Gradle wrapper incluido en el repositorio

```bash
./gradlew assembleDebug
```

El APK debug quedará en:

```text
app/build/outputs/apk/debug/app-debug.apk
```

Consulta la guía completa en [`docs/GUIA_COMPILACION.md`](docs/GUIA_COMPILACION.md).

## Documentación

- [`docs/ESPECIFICACION_PROYECTO.md`](docs/ESPECIFICACION_PROYECTO.md) — alcance, decisiones técnicas y modelo de datos.
- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) — estructura del código, capas y flujo de datos.
- [`docs/GUIA_COMPILACION.md`](docs/GUIA_COMPILACION.md) — cómo compilar, generar APK y publicar releases.
- [`docs/README_REPO_LIBROS.md`](docs/README_REPO_LIBROS.md) — cómo crear tu repositorio de libros compatible.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — fases de desarrollo completadas y pendientes.

## Contribuir

Las contribuciones son bienvenidas. Abre un issue o envía un pull request.

## Licencia

Este proyecto está licenciado bajo GPL-3.0. Consulta el archivo [LICENSE](LICENSE).
