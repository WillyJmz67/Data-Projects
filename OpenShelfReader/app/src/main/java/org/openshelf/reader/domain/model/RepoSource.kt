package org.openshelf.reader.domain.model

import java.net.URLEncoder

/**
 * Un repositorio público de GitHub añadido por el usuario como fuente de libros.
 *
 * El repositorio debe contener un archivo `catalog.json` en su raíz
 * con la lista de libros disponibles.
 */
data class RepoSource(
    val id: String,
    val owner: String,
    val repo: String,
    val branch: String = "main",
    val addedAt: Long = System.currentTimeMillis(),
    val enabled: Boolean = true
) {
    val catalogUrl: String
        get() = "https://raw.githubusercontent.com/$owner/$repo/$branch/catalog.json"

    fun resolveFileUrl(path: String): String {
        val clean = path.trimStart('/')
        val encodedPath = clean.split('/').joinToString("/") { segment ->
            URLEncoder.encode(segment, "UTF-8").replace("+", "%20")
        }
        return "https://raw.githubusercontent.com/$owner/$repo/$branch/$encodedPath"
    }
}
