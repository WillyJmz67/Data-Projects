package org.openshelf.reader.ui.navigation

import android.net.Uri

sealed class Screen(val route: String) {
    data object Library : Screen("library")
    data object Repositories : Screen("repositories")
    data object RemoteCatalog : Screen("remote_catalog/{repoId}") {
        fun createRoute(repoId: String): String = "remote_catalog/${Uri.encode(repoId)}"
    }
    data object Settings : Screen("settings")
}
