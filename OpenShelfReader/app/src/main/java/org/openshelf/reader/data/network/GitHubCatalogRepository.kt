package org.openshelf.reader.data.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import org.openshelf.reader.domain.model.RemoteCatalog
import org.openshelf.reader.domain.model.RepoSource

/**
 * Descarga y parsea el archivo catalog.json de un repositorio público de GitHub.
 */
class GitHubCatalogRepository(
    private val client: OkHttpClient,
    private val json: Json
) {
    suspend fun fetchCatalog(source: RepoSource): Result<RemoteCatalog> =
        withContext(Dispatchers.IO) {
            runCatching {
                val request = Request.Builder()
                    .url(source.catalogUrl)
                    .header("User-Agent", "OpenShelfReader")
                    .build()

                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        error("HTTP ${response.code} al descargar catalog.json")
                    }
                    val body = response.body?.string().orEmpty()
                    json.decodeFromString<RemoteCatalog>(body)
                }
            }
        }
}
