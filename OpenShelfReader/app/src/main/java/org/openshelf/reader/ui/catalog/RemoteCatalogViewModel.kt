package org.openshelf.reader.ui.catalog

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import org.openshelf.reader.OpenShelfApp
import org.openshelf.reader.domain.model.RemoteBook
import org.openshelf.reader.domain.model.RepoSource

class RemoteCatalogViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = (app as OpenShelfApp).container.libraryRepository

    private val _state = MutableStateFlow<CatalogState>(CatalogState.Loading)
    val state: StateFlow<CatalogState> = _state

    private val _downloadingIds = MutableStateFlow<Set<String>>(emptySet())
    val downloadingIds: StateFlow<Set<String>> = _downloadingIds

    private val _downloadedIds = MutableStateFlow<Set<String>>(emptySet())
    val downloadedIds: StateFlow<Set<String>> = _downloadedIds

    fun load(repoId: String) {
        viewModelScope.launch {
            _state.value = CatalogState.Loading

            val source = repo.findRepoById(repoId)
            if (source == null) {
                _state.value = CatalogState.Error("Repositorio no encontrado ($repoId)")
                return@launch
            }

            repo.fetchCatalog(source).fold(
                onSuccess = { catalog ->
                    _state.value = CatalogState.Loaded(source, catalog.books)
                },
                onFailure = { e ->
                    _state.value = CatalogState.Error(e.message ?: "Error desconocido")
                }
            )
        }
    }

    fun download(source: RepoSource, book: RemoteBook) {
        viewModelScope.launch {
            _downloadingIds.value = _downloadingIds.value + book.id
            repo.downloadRemoteBook(source, book).fold(
                onSuccess = {
                    _downloadingIds.value = _downloadingIds.value - book.id
                    _downloadedIds.value = _downloadedIds.value + book.id
                },
                onFailure = {
                    _downloadingIds.value = _downloadingIds.value - book.id
                }
            )
        }
    }
}

sealed interface CatalogState {
    data object Loading : CatalogState
    data class Loaded(val source: RepoSource, val books: List<RemoteBook>) : CatalogState
    data class Error(val message: String) : CatalogState
}
