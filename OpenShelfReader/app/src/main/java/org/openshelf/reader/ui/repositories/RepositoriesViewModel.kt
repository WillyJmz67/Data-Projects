package org.openshelf.reader.ui.repositories

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.openshelf.reader.OpenShelfApp
import org.openshelf.reader.domain.model.RepoSource

class RepositoriesViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = (app as OpenShelfApp).container.libraryRepository

    val repos = repo.observeRepos()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun addRepo(input: String) {
        val parsed = parseRepo(input) ?: return
        viewModelScope.launch {
            repo.addRepo(parsed.first, parsed.second, parsed.third)
        }
    }

    fun remove(id: String) {
        viewModelScope.launch { repo.removeRepo(id) }
    }

    /**
     * Acepta "usuario/repositorio", "https://github.com/usuario/repositorio"
     * o "https://github.com/usuario/repositorio/tree/rama".
     */
    private fun parseRepo(input: String): Triple<String, String, String>? {
        val cleaned = input.trim().removeSuffix("/")
        val regex = Regex("""(?:https?://(?:www\.)?github\.com/)?([^/\s]+)/([^/\s]+?)(?:/tree/([^/\s]+))?/?""")
        val match = regex.matchEntire(cleaned) ?: return null
        val owner = match.groupValues[1]
        val repoName = match.groupValues[2].removeSuffix(".git")
        val branch = match.groupValues[3].ifEmpty { "main" }
        if (owner.isBlank() || repoName.isBlank()) return null
        return Triple(owner, repoName, branch)
    }
}
