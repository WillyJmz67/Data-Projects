package org.openshelf.reader.ui.navigation

import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import org.openshelf.reader.ui.catalog.RemoteCatalogScreen
import org.openshelf.reader.ui.library.LibraryScreen
import org.openshelf.reader.ui.repositories.RepositoriesScreen
import org.openshelf.reader.ui.settings.SettingsScreen

@Composable
fun OpenShelfNavHost(navController: NavHostController) {
    NavHost(navController = navController, startDestination = Screen.Library.route) {
        composable(Screen.Library.route) {
            LibraryScreen()
        }
        composable(Screen.Repositories.route) {
            RepositoriesScreen(
                onOpenCatalog = { repoId ->
                    navController.navigate(Screen.RemoteCatalog.createRoute(repoId))
                }
            )
        }
        composable(
            route = Screen.RemoteCatalog.route,
            arguments = listOf(navArgument("repoId") { type = NavType.StringType })
        ) { backStackEntry ->
            val encodedRepoId = backStackEntry.arguments?.getString("repoId").orEmpty()
            val repoId = Uri.decode(encodedRepoId)
            RemoteCatalogScreen(
                repoId = repoId,
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.Settings.route) {
            SettingsScreen()
        }
    }
}
