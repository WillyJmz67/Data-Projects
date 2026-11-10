package org.openshelf.reader.domain.model

enum class BookFormat(val extension: String) {
    EPUB("epub"),
    PDF("pdf"),
    CBZ("cbz"),
    CBR("cbr"),
    UNKNOWN("bin");

    companion object {
        fun fromFileName(name: String): BookFormat {
            val ext = name.substringAfterLast('.', "").lowercase()
            return entries.firstOrNull { it.extension == ext } ?: UNKNOWN
        }
    }
}
