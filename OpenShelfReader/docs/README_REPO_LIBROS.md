# Crear tu repositorio de libros para OpenShelf Reader

OpenShelf Reader descarga libros desde repositorios **públicos** de GitHub que contengan un archivo `catalog.json` en su raíz.

## 1. Estructura del repositorio

```text
mi-biblioteca/
├── catalog.json          <- obligatorio, en la raíz
├── covers/               <- opcional: portadas
│   ├── don-quijote.jpg
│   └── manga-ejemplo.jpg
└── books/                <- archivos de los libros
    ├── don-quijote.epub
    ├── manual.pdf
    └── manga-ejemplo.cbz
```

> La rama por defecto que lee la app es `main`. Si tu repositorio usa otra rama, añádela con el formato `usuario/repositorio/tree/nombre-de-rama`.

## 2. Formato de `catalog.json`

```json
{
  "name": "Biblioteca OpenShelf",
  "description": "Repositorio público de libros y cómics",
  "books": [
    {
      "id": "don-quijote-epub",
      "title": "Don Quijote de la Mancha",
      "author": "Miguel de Cervantes",
      "file": "books/don-quijote.epub",
      "cover": "covers/don-quijote.jpg",
      "type": "epub",
      "collection": "Clásicos",
      "language": "es",
      "description": "Novela clásica de la literatura española."
    },
    {
      "id": "manual-pdf",
      "title": "Manual de ejemplo",
      "author": "Autor desconocido",
      "file": "books/manual.pdf",
      "cover": "covers/manual.jpg",
      "type": "pdf",
      "collection": "Documentos",
      "language": "es"
    },
    {
      "id": "manga-ejemplo-vol-1",
      "title": "Manga Ejemplo",
      "author": "Autor del manga",
      "file": "books/manga-ejemplo-v01.cbz",
      "cover": "covers/manga-ejemplo-v01.jpg",
      "type": "cbz",
      "collection": "Manga",
      "language": "es",
      "readingDirection": "rtl"
    }
  ]
}
```

## 3. Campos de cada libro

| Campo | Obligatorio | Tipo | Descripción |
|---|---|---|---|
| `id` | ✅ | string | Identificador único del libro en el catálogo (se usa como clave en la biblioteca) |
| `title` | ✅ | string | Título visible |
| `file` | ✅ | string | Ruta del archivo **relativa a la raíz del repo** (ej. `books/libro.epub`) |
| `author` | ❌ | string | Autor |
| `cover` | ❌ | string | Ruta de la portada relativa a la raíz (jpg/png/webp) |
| `type` | ❌ | string | `epub`, `pdf`, `cbz`… Si falta, se deduce de la extensión de `file` |
| `collection` | ❌ | string | Colección (ej. «Manga», «Clásicos») |
| `language` | ❌ | string | Código de idioma (ej. `es`, `en`) |
| `description` | ❌ | string | Descripción breve |
| `readingDirection` | ❌ | string | `rtl` para manga japonés (no usado aún por el lector CBZ, que conmuta manualmente) |

## 4. Reglas importantes

- **Repositorio público**: la app no usa tokens ni cuentas, así que solo puede leer repos públicos.
- **Tamaño de archivos**: GitHub permite archivos de hasta **100 MB** en un repo normal. Para libros más grandes usa GitHub Releases en el repo de libros y enlaza el archivo… (enlaces externos completos llegarán en fase 2; por ahora, mantén los archivos ≤ 100 MB).
- **Contenido legal**: sube únicamente contenido de dominio público, con licencia libre o del que tengas derechos. GitHub puede eliminar repos con contenido protegido, y la app no está pensada para piratear contenido.
- **Formatos soportados** (fase 1): `.epub`, `.pdf`, `.cbz`. CBR/CB7/TXT están planificados.
- **Orden del catálogo**: los libros aparecen en el orden en que estén en el array `books`.
- **Actualizaciones**: si cambias un archivo del repo, quien ya lo descargó conserva su copia local; la re-descarga sobrescribe el archivo local (mismo `id`).

## 5. URLs que usa la app

Para un repo `usuario/mi-biblioteca` en la rama `main`:

```text
Catálogo:  https://raw.githubusercontent.com/usuario/mi-biblioteca/main/catalog.json
Libro:     https://raw.githubusercontent.com/usuario/mi-biblioteca/main/books/don-quijote.epub
Portada:   https://raw.githubusercontent.com/usuario/mi-biblioteca/main/covers/don-quijote.jpg
```

`raw.githubusercontent.com` sirve archivos sin límites de API ni tokens para repos públicos.

## 6. Checklist antes de compartir tu repo de libros

- [ ] `catalog.json` válido en la raíz (valida el JSON en jsonlint.com).
- [ ] Cada `file` y `cover` existe realmente en el repo (rutas exactas, sensibles a mayúsculas).
- [ ] Todos los `id` son únicos.
- [ ] Archivos ≤ 100 MB.
- [ ] Contenido legal / dominio público.
- [ ] Repo público.
