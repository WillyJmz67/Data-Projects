package org.openshelf.reader.di

import android.content.Context
import androidx.room.Room
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import org.openshelf.reader.data.db.OpenShelfDatabase
import org.openshelf.reader.data.network.DownloadService
import org.openshelf.reader.data.network.GitHubCatalogRepository
import org.openshelf.reader.data.repository.LibraryRepository

/**
 * Contenedor de dependencias manual (sin Hilt) para simplificar la configuración inicial.
 * Todas las dependencias son singletons a nivel de aplicación.
 */
class AppContainer(context: Context) {

    val database: OpenShelfDatabase = Room.databaseBuilder(
        context,
        OpenShelfDatabase::class.java,
        "openshelf.db"
    ).build()

    val json: Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
    }

    val httpClient: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(
            HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            }
        )
        .build()

    val catalogRepository: GitHubCatalogRepository =
        GitHubCatalogRepository(httpClient, json)

    val downloadService: DownloadService =
        DownloadService(httpClient, context)

    val libraryRepository: LibraryRepository = LibraryRepository(
        bookDao = database.bookDao(),
        progressDao = database.progressDao(),
        repoDao = database.repoSourceDao(),
        catalogRepository = catalogRepository,
        downloadService = downloadService
    )
}
