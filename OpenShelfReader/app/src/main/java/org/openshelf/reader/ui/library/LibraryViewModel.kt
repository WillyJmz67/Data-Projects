package org.openshelf.reader.ui.library

import android.app.Application
import android.content.Context
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.openshelf.reader.OpenShelfApp
import org.openshelf.reader.domain.model.Book

sealed interface ImportState {
    data object Idle : ImportState
    data object Importing : ImportState
    data class Success(val count: Int) : ImportState
    data class Error(val message: String) : ImportState
}

class LibraryViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = (app as OpenShelfApp).container.libraryRepository

    val books = repo.observeBooks()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _importState = MutableStateFlow<ImportState>(ImportState.Idle)
    val importState: StateFlow<ImportState> = _importState

    fun importFiles(uris: List<Uri>, context: Context) {
        if (uris.isEmpty()) return
        viewModelScope.launch {
            _importState.value = ImportState.Importing
            repo.importLocalFiles(uris, context).fold(
                onSuccess = { count ->
                    _importState.value = ImportState.Success(count)
                },
                onFailure = { e ->
                    _importState.value = ImportState.Error(e.message ?: "Error al importar")
                }
            )
        }
    }

    fun importFolder(folderUri: Uri, context: Context) {
        viewModelScope.launch {
            _importState.value = ImportState.Importing
            repo.importLocalFolder(folderUri, context).fold(
                onSuccess = { count ->
                    _importState.value = ImportState.Success(count)
                },
                onFailure = { e ->
                    _importState.value = ImportState.Error(e.message ?: "Error al importar carpeta")
                }
            )
        }
    }

    fun clearImportState() {
        _importState.value = ImportState.Idle
    }

    fun delete(book: Book) {
        viewModelScope.launch { repo.deleteBook(book.id) }
    }
}
