package org.openshelf.reader.ui.catalog

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import org.openshelf.reader.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RemoteCatalogScreen(
    repoId: String,
    onBack: () -> Unit,
    viewModel: RemoteCatalogViewModel = viewModel()
) {
    LaunchedEffect(repoId) { viewModel.load(repoId) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    val downloadingIds by viewModel.downloadingIds.collectAsStateWithLifecycle()
    val downloadedIds by viewModel.downloadedIds.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text(stringResource(R.string.catalog_title)) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = stringResource(R.string.reader_back)
                    )
                }
            }
        )

        when (val s = state) {
            CatalogState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }

            is CatalogState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(stringResource(R.string.catalog_error, s.message))
            }

            is CatalogState.Loaded -> LazyColumn(
                contentPadding = PaddingValues(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(s.books, key = { it.id }) { book ->
                    val isDownloading = downloadingIds.contains(book.id)
                    val isDownloaded = downloadedIds.contains(book.id)

                    ListItem(
                        headlineContent = { Text(book.title) },
                        supportingContent = {
                            Text(book.author ?: stringResource(R.string.catalog_unknown_author))
                        },
                        trailingContent = {
                            when {
                                isDownloading -> {
                                    CircularProgressIndicator()
                                }
                                isDownloaded -> {
                                    OutlinedButton(onClick = {}, enabled = false) {
                                        Text(stringResource(R.string.catalog_downloaded))
                                    }
                                }
                                else -> {
                                    Button(onClick = { viewModel.download(s.source, book) }) {
                                        Text(stringResource(R.string.catalog_download))
                                    }
                                }
                            }
                        }
                    )
                }
            }
        }
    }
}
