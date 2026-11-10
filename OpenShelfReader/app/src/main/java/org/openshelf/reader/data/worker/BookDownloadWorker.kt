package org.openshelf.reader.data.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import org.openshelf.reader.OpenShelfApp

/**
 * Descarga un libro en segundo plano usando WorkManager.
 * La UI puede encolar la descarga y seguir navegando.
 */
class BookDownloadWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val repoId = inputData.getString(KEY_REPO_ID) ?: return Result.failure()
        val bookId = inputData.getString(KEY_BOOK_ID) ?: return Result.failure()

        val app = applicationContext as OpenShelfApp
        val library = app.container.libraryRepository

        val repo = library.findRepoById(repoId) ?: return Result.failure()
        val catalog = library.fetchCatalog(repo).getOrNull()
            ?: return Result.retry()

        val remote = catalog.books.firstOrNull { it.id == bookId }
            ?: return Result.failure()

        return library
            .downloadRemoteBook(repo, remote)
            .fold(
                onSuccess = { Result.success() },
                onFailure = { Result.retry() }
            )
    }

    companion object {
        const val KEY_REPO_ID = "repo_id"
        const val KEY_BOOK_ID = "book_id"

        fun enqueue(context: Context, repoId: String, bookId: String) {
            val data = Data.Builder()
                .putString(KEY_REPO_ID, repoId)
                .putString(KEY_BOOK_ID, bookId)
                .build()

            val request = OneTimeWorkRequestBuilder<BookDownloadWorker>()
                .setInputData(data)
                .build()

            WorkManager.getInstance(context).enqueue(request)
        }
    }
}
