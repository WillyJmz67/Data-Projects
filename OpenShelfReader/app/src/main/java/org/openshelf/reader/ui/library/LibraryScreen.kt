package org.openshelf.reader.ui.library

import android.content.Intent
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import org.openshelf.reader.R
import org.openshelf.reader.domain.model.Book
import org.openshelf.reader.ui.components.BookCover
import org.openshelf.reader.ui.reader.ReaderActivity

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(
    viewModel: LibraryViewModel = viewModel()
) {
    val context = LocalContext.current
    val books by viewModel.books.collectAsStateWithLifecycle()
    val importState by viewModel.importState.collectAsStateWithLifecycle()

    var bookToDelete by remember { mutableStateOf<Book?>(null) }
    var showFabMenu by remember { mutableStateOf(false) }

    val folderLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree()
    ) { uri ->
        uri?.let { viewModel.importFolder(it, context) }
    }

    val fileLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        if (uris.isNotEmpty()) {
            viewModel.importFiles(uris, context)
        }
    }

    LaunchedEffect(importState) {
        when (val state = importState) {
            is ImportState.Success -> {
                Toast.makeText(
                    context,
                    context.getString(R.string.library_import_success, state.count),
                    Toast.LENGTH_SHORT
                ).show()
                viewModel.clearImportState()
            }
            is ImportState.Error -> {
                Toast.makeText(
                    context,
                    context.getString(R.string.library_import_error, state.message),
                    Toast.LENGTH_LONG
                ).show()
                viewModel.clearImportState()
            }
            else -> {}
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.library_title)) },
                actions = {
                    IconButton(onClick = { folderLauncher.launch(null) }) {
                        Icon(
                            Icons.Filled.FolderOpen,
                            contentDescription = stringResource(R.string.library_import_folder)
                        )
                    }
                    IconButton(onClick = {
                        fileLauncher.launch(
                            arrayOf(
                                "application/epub+zip",
                                "application/pdf",
                                "application/x-cbz",
                                "application/zip",
                                "*/*"
                            )
                        )
                    }) {
                        Icon(
                            Icons.Filled.UploadFile,
                            contentDescription = stringResource(R.string.library_import_files)
                        )
                    }
                }
            )
        },
        floatingActionButton = {
            Box {
                FloatingActionButton(onClick = { showFabMenu = true }) {
                    Icon(Icons.Filled.Add, contentDescription = null)
                }

                DropdownMenu(
                    expanded = showFabMenu,
                    onDismissRequest = { showFabMenu = false }
                ) {
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.library_import_folder)) },
                        leadingIcon = { Icon(Icons.Filled.FolderOpen, contentDescription = null) },
                        onClick = {
                            showFabMenu = false
                            folderLauncher.launch(null)
                        }
                    )
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.library_import_files)) },
                        leadingIcon = { Icon(Icons.Filled.UploadFile, contentDescription = null) },
                        onClick = {
                            showFabMenu = false
                            fileLauncher.launch(
                                arrayOf(
                                    "application/epub+zip",
                                    "application/pdf",
                                    "application/x-cbz",
                                    "application/zip",
                                    "*/*"
                                )
                            )
                        }
                    )
                }
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (books.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        stringResource(R.string.library_empty),
                        modifier = Modifier.padding(32.dp),
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(minSize = 140.dp),
                    contentPadding = PaddingValues(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(books, key = { it.id }) { book ->
                        BookCard(
                            book = book,
                            onLongClick = { bookToDelete = book }
                        )
                    }
                }
            }

            if (importState is ImportState.Importing) {
                Dialog(onDismissRequest = {}) {
                    Surface(
                        shape = MaterialTheme.shapes.medium,
                        tonalElevation = 8.dp
                    ) {
                        Row(
                            modifier = Modifier.padding(24.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            CircularProgressIndicator(Modifier.size(36.dp))
                            Spacer(Modifier.width(16.dp))
                            Text(stringResource(R.string.library_importing))
                        }
                    }
                }
            }

            bookToDelete?.let { book ->
                AlertDialog(
                    onDismissRequest = { bookToDelete = null },
                    title = { Text(stringResource(R.string.library_delete_book)) },
                    text = { Text(stringResource(R.string.library_delete_confirm, book.title)) },
                    confirmButton = {
                        TextButton(onClick = {
                            viewModel.delete(book)
                            bookToDelete = null
                        }) {
                            Text(stringResource(R.string.repositories_delete))
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { bookToDelete = null }) {
                            Text(stringResource(R.string.reader_back))
                        }
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun BookCard(
    book: Book,
    onLongClick: () -> Unit
) {
    val context = LocalContext.current

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .combinedClickable(
                onClick = {
                    val path = book.localPath
                    if (path != null) {
                        val intent = Intent(
                            context,
                            ReaderActivity::class.java
                        ).apply {
                            putExtra("book_id", book.id)
                            putExtra("book_path", path)
                        }
                        context.startActivity(intent)
                    }
                },
                onLongClick = onLongClick
            )
    ) {
        Column(Modifier.padding(8.dp)) {
            BookCover(
                coverPath = book.coverPath,
                contentDescription = book.title,
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(2f / 3f)
            )

            Text(
                text = book.title,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(top = 8.dp)
            )

            book.author?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}
