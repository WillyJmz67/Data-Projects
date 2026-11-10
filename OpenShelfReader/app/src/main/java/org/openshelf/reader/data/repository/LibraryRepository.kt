package org.openshelf.reader.data.repository

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import org.openshelf.reader.data.db.dao.BookDao
import org.openshelf.reader.data.db.dao.ProgressDao
import org.openshelf.reader.data.db.dao.RepoSourceDao
import org.openshelf.reader.data.db.entity.BookEntity
import org.openshelf.reader.data.db.entity.ReadingProgressEntity
import org.openshelf.reader.data.db.entity.RepoSourceEntity
import org.openshelf.reader.data.network.DownloadService
import org.openshelf.reader.data.network.GitHubCatalogRepository
import org.openshelf.reader.domain.model.Book
import org.openshelf.reader.domain.model.BookFormat
import org.openshelf.reader.domain.model.RemoteBook
import org.openshelf.reader.domain.model.RemoteCatalog
import org.openshelf.reader.domain.model.RepoSource
import org.openshelf.reader.epub.EpubParser
import java.util.UUID
import java.io.File as JavaFile

class LibraryRepository(
    private val bookDao: BookDao,
    private val progressDao: ProgressDao,
    private val repoDao: RepoSourceDao,
    private val catalogRepository: GitHubCatalogRepository,
    private val downloadService: DownloadService
) {
    // ---------------------------------------------------------------------
    // Consultas observables
    // ---------------------------------------------------------------------

    fun observeBooks(): Flow<List<Book>> =
        bookDao.observeAll().map { list -> list.map { it.toDomain() } }

    fun observeRepos(): Flow<List<RepoSource>> =
        repoDao.observeAll().map { list -> list.map { it.toDomain() } }

    // ---------------------------------------------------------------------
    // Repositorios GitHub
    // ---------------------------------------------------------------------

    suspend fun addRepo(owner: String, repo: String, branch: String = "main"): RepoSource {
        val id = "$owner/$repo"
        val entity = RepoSourceEntity(
            id = id, owner = owner, repo = repo, branch = branch
        )
        repoDao.upsert(entity)
        return entity.toDomain()
    }

    suspend fun removeRepo(id: String) {
        repoDao.deleteById(id)
    }

    suspend fun findRepoById(id: String): RepoSource? =
        repoDao.findById(id)?.toDomain()

    suspend fun fetchCatalog(source: RepoSource): Result<RemoteCatalog> =
        catalogRepository.fetchCatalog(source)

    // ---------------------------------------------------------------------
    // Descarga de libros remotos
    // ---------------------------------------------------------------------

    suspend fun downloadRemoteBook(
        source: RepoSource,
        remoteBook: RemoteBook
    ): Result<Book> {
        val format = BookFormat.fromFileName(remoteBook.file)
        val fileUrl = source.resolveFileUrl(remoteBook.file)
        val targetFile = downloadService.targetBookFile(remoteBook.id, format.extension)

        return downloadService.downloadFile(fileUrl, targetFile).map {
            val coverPath = remoteBook.cover?.let { coverRel ->
                val coverUrl = source.resolveFileUrl(coverRel)
                val ext = coverRel.substringAfterLast('.', "jpg")
                val coverFile = downloadService.targetCoverFile(remoteBook.id, ext)
                downloadService.downloadFile(coverUrl, coverFile).getOrNull()?.absolutePath
            }

            val entity = BookEntity(
                id = remoteBook.id,
                title = remoteBook.title,
                author = remoteBook.author,
                format = format.extension,
                localPath = targetFile.absolutePath,
                remoteUrl = fileUrl,
                coverPath = coverPath,
                collectionName = remoteBook.collection,
                language = remoteBook.language,
                repoId = source.id,
                addedAt = System.currentTimeMillis()
            )
            bookDao.upsert(entity)
            entity.toDomain()
        }
    }

    // ---------------------------------------------------------------------
    // Importación local (archivos y carpetas)
    // ---------------------------------------------------------------------

    suspend fun importLocalFiles(uris: List<Uri>, context: Context): Result<Int> =
        withContext(Dispatchers.IO) {
            runCatching {
                var importedCount = 0
                for (uri in uris) {
                    if (importSingleUri(uri, context) != null) {
                        importedCount++
                    }
                }
                importedCount
            }
        }

    suspend fun importLocalFolder(folderUri: Uri, context: Context): Result<Int> =
        withContext(Dispatchers.IO) {
            runCatching {
                runCatching {
                    context.contentResolver.takePersistableUriPermission(
                        folderUri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION
                    )
                }

                val rootDoc = DocumentFile.fromTreeUri(context, folderUri)
                    ?: error("No se pudo acceder a la carpeta seleccionada")

                val filesToImport = mutableListOf<DocumentFile>()
                collectBookDocuments(rootDoc, filesToImport)

                var importedCount = 0
                for (doc in filesToImport) {
                    if (importSingleUri(doc.uri, context, doc.name) != null) {
                        importedCount++
                    }
                }
                importedCount
            }
        }

    private fun collectBookDocuments(dir: DocumentFile, result: MutableList<DocumentFile>) {
        val children = dir.listFiles()
        for (child in children) {
            if (child.isDirectory) {
                collectBookDocuments(child, result)
            } else if (child.isFile) {
                val name = child.name.orEmpty()
                if (BookFormat.fromFileName(name) != BookFormat.UNKNOWN) {
                    result.add(child)
                }
            }
        }
    }

    private fun importSingleUri(
        uri: Uri,
        context: Context,
        fallbackName: String? = null
    ): Book? {
        val fileName = fallbackName
            ?: getUriFileName(context, uri)
            ?: "libro_${System.currentTimeMillis()}"

        val format = BookFormat.fromFileName(fileName)
        if (format == BookFormat.UNKNOWN) return null

        val bookId = "local_${System.currentTimeMillis()}_${UUID.randomUUID().toString().take(8)}"
        val targetFile = downloadService.targetBookFile(bookId, format.extension)

        val copied = runCatching {
            context.contentResolver.openInputStream(uri)?.use { input ->
                targetFile.parentFile?.mkdirs()
                targetFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
            targetFile.exists() && targetFile.length() > 0
        }.getOrDefault(false)

        if (!copied) return null

        var parsedTitle: String? = null
        var parsedAuthor: String? = null

        if (format == BookFormat.EPUB) {
            runCatching {
                val tempExtract = JavaFile(context.filesDir, "temp_epub_$bookId")
                val manifest = EpubParser.parse(targetFile, tempExtract)
                parsedTitle = manifest.title
                parsedAuthor = manifest.author
            }
        }

        val title = parsedTitle.orEmpty().ifBlank { fileName.substringBeforeLast('.') }
        val author = parsedAuthor.orEmpty().ifBlank { "Local" }

        val entity = BookEntity(
            id = bookId,
            title = title,
            author = author,
            format = format.extension,
            localPath = targetFile.absolutePath,
            remoteUrl = null,
            coverPath = null,
            collectionName = null,
            language = null,
            repoId = "local",
            addedAt = System.currentTimeMillis()
        )

        runBlocking { bookDao.upsert(entity) }
        return entity.toDomain()
    }

    private fun getUriFileName(context: Context, uri: Uri): String? {
        if (uri.scheme == "content") {
            context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (nameIndex != -1) {
                        return cursor.getString(nameIndex)
                    }
                }
            }
        }
        return uri.path?.substringAfterLast('/')
    }

    // ---------------------------------------------------------------------
    // Gestión de libros
    // ---------------------------------------------------------------------

    suspend fun deleteBook(id: String) {
        bookDao.findById(id)?.let { book ->
            book.localPath?.let { path ->
                runCatching { JavaFile(path).delete() }
            }
            book.coverPath?.let { path ->
                runCatching { JavaFile(path).delete() }
            }
        }
        bookDao.deleteById(id)
    }

    suspend fun getBook(id: String): Book? = bookDao.findById(id)?.toDomain()

    // ---------------------------------------------------------------------
    // Progreso de lectura
    // ---------------------------------------------------------------------

    suspend fun getProgress(bookId: String): ReadingProgressEntity? {
        return progressDao.forBook(bookId)
    }

    suspend fun saveProgress(
        bookId: String,
        location: String,
        percent: Float
    ) {
        val progress = ReadingProgressEntity(
            bookId = bookId,
            location = location,
            page = null,
            percent = percent,
            updatedAt = System.currentTimeMillis()
        )

        progressDao.upsert(progress)

        bookDao.findById(bookId)?.let { book ->
            bookDao.update(
                book.copy(
                    progressLocation = location,
                    progressPercent = percent,
                    lastReadAt = System.currentTimeMillis()
                )
            )
        }
    }

    // ---------------------------------------------------------------------
    // Mapeos entidad -> dominio
    // ---------------------------------------------------------------------

    private fun BookEntity.toDomain(): Book = Book(
        id = id,
        title = title,
        author = author,
        format = BookFormat.fromFileName("x.$format"),
        localPath = localPath,
        remoteUrl = remoteUrl,
        coverPath = coverPath,
        collection = collectionName,
        language = language,
        repoId = repoId,
        addedAt = addedAt,
        lastReadAt = lastReadAt,
        progressPercent = progressPercent,
        isFavorite = isFavorite
    )

    private fun RepoSourceEntity.toDomain(): RepoSource = RepoSource(
        id = id,
        owner = owner,
        repo = repo,
        branch = branch,
        addedAt = addedAt,
        enabled = enabled
    )
}
