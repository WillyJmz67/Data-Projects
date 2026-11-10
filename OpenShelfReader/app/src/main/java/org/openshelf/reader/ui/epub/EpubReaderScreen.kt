package org.openshelf.reader.ui.epub

import android.annotation.SuppressLint
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.List
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.openshelf.reader.OpenShelfApp
import org.openshelf.reader.R
import org.openshelf.reader.epub.EpubChapter
import org.openshelf.reader.epub.EpubParser
import org.openshelf.reader.epub.EpubTocItem
import java.io.File

private sealed interface EpubUiState {
    data object Loading : EpubUiState
    data class Error(val message: String) : EpubUiState
    data class Loaded(
        val title: String?,
        val chapters: List<EpubChapter>,
        val toc: List<EpubTocItem>,
        val initialChapter: Int
    ) : EpubUiState
}

@Composable
fun EpubReaderScreen(
    bookId: String,
    filePath: String,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val app = context.applicationContext as OpenShelfApp
    val repository = app.container.libraryRepository

    var state by remember { mutableStateOf<EpubUiState>(EpubUiState.Loading) }

    LaunchedEffect(filePath) {
        val progress = repository.getProgress(bookId)
        val initialChapter = parseEpubLocation(progress?.location)

        val result = withContext(Dispatchers.IO) {
            runCatching {
                val epubFile = File(filePath)
                val destDir = File(context.filesDir, "epubs/$bookId")
                EpubParser.parse(epubFile, destDir)
            }
        }

        state = result.fold(
            onSuccess = { manifest ->
                if (manifest.chapters.isEmpty()) {
                    EpubUiState.Error(context.getString(R.string.reader_no_chapters))
                } else {
                    EpubUiState.Loaded(
                        title = manifest.title,
                        chapters = manifest.chapters,
                        toc = manifest.toc,
                        initialChapter = initialChapter.coerceIn(0, manifest.chapters.size - 1)
                    )
                }
            },
            onFailure = { error ->
                EpubUiState.Error(error.message ?: context.getString(R.string.reader_open_epub_error))
            }
        )
    }

    when (val current = state) {
        EpubUiState.Loading -> {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        }

        is EpubUiState.Error -> {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(current.message, modifier = Modifier.padding(32.dp))
            }
        }

        is EpubUiState.Loaded -> {
            var currentIndex by remember(current) {
                mutableStateOf(current.initialChapter)
            }

            var showToc by remember { mutableStateOf(false) }

            val chapter = current.chapters.getOrNull(currentIndex)

            // Guardar progreso al cambiar de capítulo
            LaunchedEffect(currentIndex) {
                val percent = if (current.chapters.size <= 1) {
                    1f
                } else {
                    currentIndex.toFloat() / (current.chapters.size - 1)
                }

                repository.saveProgress(
                    bookId = bookId,
                    location = "epub:chapter=$currentIndex",
                    percent = percent
                )
            }

            Column(Modifier.fillMaxSize()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.surface)
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = stringResource(R.string.reader_back))
                    }

                    Text(
                        text = current.title ?: "EPUB",
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.weight(1f)
                    )

                    Box {
                        IconButton(onClick = { showToc = true }) {
                            Icon(Icons.Filled.List, contentDescription = stringResource(R.string.reader_toc))
                        }

                        DropdownMenu(
                            expanded = showToc,
                            onDismissRequest = { showToc = false }
                        ) {
                            if (current.toc.isNotEmpty()) {
                                current.toc.forEach { item ->
                                    DropdownMenuItem(
                                        text = { Text(item.title) },
                                        onClick = {
                                            showToc = false

                                            val targetIndex = current.chapters.indexOfFirst {
                                                item.absolutePath != null && it.absolutePath == item.absolutePath
                                            }

                                            if (targetIndex >= 0) {
                                                currentIndex = targetIndex
                                            } else {
                                                val byHref = current.chapters.indexOfFirst {
                                                    it.absolutePath.endsWith(item.href.substringAfterLast('/'))
                                                }
                                                if (byHref >= 0) currentIndex = byHref
                                            }
                                        }
                                    )
                                }
                            } else {
                                current.chapters.forEachIndexed { index, _ ->
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.reader_chapter, index + 1)) },
                                        onClick = {
                                            showToc = false
                                            currentIndex = index
                                        }
                                    )
                                }
                            }
                        }
                    }
                }

                if (chapter != null) {
                    EpubWebView(
                        chapter = chapter,
                        modifier = Modifier.weight(1f)
                    )
                } else {
                    Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                        Text(stringResource(R.string.reader_chapter_unavailable))
                    }
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    TextButton(
                        onClick = {
                            if (currentIndex > 0) currentIndex--
                        },
                        enabled = currentIndex > 0
                    ) {
                        Icon(Icons.Filled.ChevronLeft, contentDescription = stringResource(R.string.reader_previous))
                        Text(stringResource(R.string.reader_previous))
                    }

                    Text(stringResource(R.string.reader_page_of, currentIndex + 1, current.chapters.size))

                    TextButton(
                        onClick = {
                            if (currentIndex < current.chapters.size - 1) currentIndex++
                        },
                        enabled = currentIndex < current.chapters.size - 1
                    ) {
                        Text(stringResource(R.string.reader_next))
                        Icon(Icons.Filled.ChevronRight, contentDescription = stringResource(R.string.reader_next))
                    }
                }
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun EpubWebView(
    chapter: EpubChapter,
    modifier: Modifier = Modifier
) {
    val isDark = isSystemInDarkTheme()

    key(chapter.absolutePath, isDark) {
        AndroidView(
            modifier = modifier.fillMaxSize(),
            factory = { context ->
                WebView(context).apply {
                    settings.allowFileAccess = true
                    settings.allowContentAccess = true
                    @Suppress("DEPRECATION")
                    settings.allowFileAccessFromFileURLs = true
                    @Suppress("DEPRECATION")
                    settings.allowUniversalAccessFromFileURLs = true
                    settings.builtInZoomControls = true
                    settings.displayZoomControls = false
                    settings.setSupportZoom(true)
                    // Necesario para aplicar el modo oscuro vía JavaScript sobre contenido local
                    settings.javaScriptEnabled = true

                    setBackgroundColor(Color.Transparent.toArgb())

                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            super.onPageFinished(view, url)

                            val js = if (isDark) {
                                """
                                (function() {
                                    document.documentElement.style.background = '#111111';
                                    document.documentElement.style.color = '#dddddd';
                                    document.documentElement.style.filter = 'invert(1) hue-rotate(180deg)';
                                })();
                                """.trimIndent()
                            } else {
                                """
                                (function() {
                                    document.documentElement.style.filter = '';
                                })();
                                """.trimIndent()
                            }

                            view?.evaluateJavascript(js, null)
                        }
                    }

                    loadUrl("file://" + chapter.absolutePath)
                }
            }
        )
    }
}

private fun parseEpubLocation(location: String?): Int {
    if (location == null) return 0

    return location
        .substringAfter("chapter=", "")
        .toIntOrNull()
        ?: 0
}
