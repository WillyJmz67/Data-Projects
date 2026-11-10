package org.openshelf.reader.data.network

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File

/**
 * Descarga archivos (libros y portadas) desde raw.githubusercontent.com
 * y los guarda en el almacenamiento interno privado de la app.
 */
class DownloadService(
    private val client: OkHttpClient,
    private val context: Context
) {
    private val booksDir: File
        get() = File(context.filesDir, "books").apply { mkdirs() }

    private val coversDir: File
        get() = File(context.filesDir, "covers").apply { mkdirs() }

    suspend fun downloadFile(url: String, targetFile: File): Result<File> =
        withContext(Dispatchers.IO) {
            runCatching {
                val request = Request.Builder()
                    .url(url)
                    .header("User-Agent", "OpenShelfReader")
                    .build()

                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        error("HTTP ${response.code} al descargar: $url")
                    }
                    val body = response.body ?: error("Respuesta vacía desde: $url")
                    targetFile.parentFile?.mkdirs()
                    body.byteStream().use { input ->
                        targetFile.outputStream().use { output ->
                            input.copyTo(output)
                        }
                    }
                }
                if (!targetFile.exists() || targetFile.length() == 0L) {
                    error("El archivo descargado está vacío")
                }
                targetFile
            }
        }

    fun targetBookFile(bookId: String, extension: String): File =
        File(booksDir, "$bookId.$extension")

    fun targetCoverFile(bookId: String, extension: String): File =
        File(coversDir, "$bookId.$extension")
}
