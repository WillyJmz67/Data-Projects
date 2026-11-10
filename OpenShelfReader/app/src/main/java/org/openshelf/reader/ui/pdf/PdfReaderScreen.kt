package org.openshelf.reader.ui.pdf

import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.openshelf.reader.OpenShelfApp
import org.openshelf.reader.R
import org.openshelf.reader.ui.common.ZoomableBitmap
import java.io.File

private sealed interface PdfUiState {
    data object Loading : PdfUiState
    data class Error(val message: String) : PdfUiState
    data class Loaded(
        val renderer: PdfRenderer,
        val pageCount: Int,
        val initialPage: Int
    ) : PdfUiState
}

@Composable
fun PdfReaderScreen(
    bookId: String,
    filePath: String,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val app = context.applicationContext as OpenShelfApp
    val repository = app.container.libraryRepository

    var state by remember { mutableStateOf<PdfUiState>(PdfUiState.Loading) }

    LaunchedEffect(filePath) {
        val progress = repository.getProgress(bookId)
        val savedPage = parsePdfPage(progress?.location)

        val result = withContext(Dispatchers.IO) {
            runCatching {
                val file = File(filePath)
                val fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
                PdfRenderer(fd)
            }
        }

        state = result.fold(
            onSuccess = { renderer ->
                val pageCount = renderer.pageCount

                if (pageCount <= 0) {
                    runCatching { renderer.close() }
                    PdfUiState.Error(context.getString(R.string.reader_no_pages))
                } else {
                    PdfUiState.Loaded(
                        renderer = renderer,
                        pageCount = pageCount,
                        initialPage = savedPage.coerceIn(0, pageCount - 1)
                    )
                }
            },
            onFailure = {
                PdfUiState.Error(context.getString(R.string.reader_open_pdf_error))
            }
        )
    }

    DisposableEffect(state) {
        onDispose {
            (state as? PdfUiState.Loaded)?.let {
                runCatching { it.renderer.close() }
            }
        }
    }

    when (val current = state) {
        PdfUiState.Loading -> {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        }

        is PdfUiState.Error -> {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(current.message, modifier = Modifier.padding(32.dp))
            }
        }

        is PdfUiState.Loaded -> {
            val pagerState = rememberPagerState(
                initialPage = current.initialPage,
                pageCount = { current.pageCount }
            )

            val mutex = remember { Mutex() }

            // Guardar progreso al cambiar de página
            LaunchedEffect(pagerState) {
                snapshotFlow { pagerState.currentPage }
                    .collect { page ->
                        val percent = if (current.pageCount <= 1) {
                            1f
                        } else {
                            page.toFloat() / (current.pageCount - 1)
                        }

                        repository.saveProgress(
                            bookId = bookId,
                            location = "pdf:page=$page",
                            percent = percent
                        )
                    }
            }

            HorizontalPager(
                state = pagerState,
                modifier = Modifier.fillMaxSize()
            ) { page ->
                BoxWithConstraints(Modifier.fillMaxSize()) {
                    PdfPage(
                        renderer = current.renderer,
                        mutex = mutex,
                        pageIndex = page,
                        widthPx = constraints.maxWidth,
                        heightPx = constraints.maxHeight
                    )
                }
            }
        }
    }
}

@Composable
private fun PdfPage(
    renderer: PdfRenderer,
    mutex: Mutex,
    pageIndex: Int,
    widthPx: Int,
    heightPx: Int
) {
    var bitmap by remember(pageIndex, widthPx, heightPx) {
        mutableStateOf<Bitmap?>(null)
    }
    var isError by remember(pageIndex, widthPx, heightPx) {
        mutableStateOf(false)
    }

    LaunchedEffect(pageIndex, widthPx, heightPx) {
        if (widthPx <= 0 || heightPx <= 0) return@LaunchedEffect

        val bmp = renderPdfPage(
            renderer = renderer,
            mutex = mutex,
            pageIndex = pageIndex,
            targetWidth = widthPx,
            targetHeight = heightPx
        )
        if (bmp != null) {
            bitmap = bmp
        } else {
            isError = true
        }
    }

    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        val bmp = bitmap
        when {
            bmp != null -> ZoomableBitmap(bitmap = bmp)
            isError -> Text(stringResource(R.string.reader_open_pdf_error))
            else -> CircularProgressIndicator()
        }
    }
}

/**
 * Renderiza una página del PDF a un Bitmap ajustado al tamaño de la pantalla.
 * PdfRenderer no es thread-safe: se serializa el acceso con un Mutex.
 */
private suspend fun renderPdfPage(
    renderer: PdfRenderer,
    mutex: Mutex,
    pageIndex: Int,
    targetWidth: Int,
    targetHeight: Int
): Bitmap? {
    return withContext(Dispatchers.Default) {
        runCatching {
            mutex.withLock {
                // Si el renderer ya está cerrado, openPage/render lanza IllegalStateException,
                // capturada por el runCatching exterior (isOpen() requiere API 35).
                val page = renderer.openPage(pageIndex)

                val pageWidth = page.width
                val pageHeight = page.height

                val scale = minOf(
                    targetWidth.toFloat() / pageWidth.toFloat(),
                    targetHeight.toFloat() / pageHeight.toFloat()
                )

                val bmpWidth = maxOf(1, (pageWidth * scale).toInt())
                val bmpHeight = maxOf(1, (pageHeight * scale).toInt())

                val bitmap = Bitmap.createBitmap(
                    bmpWidth,
                    bmpHeight,
                    Bitmap.Config.ARGB_8888
                )

                // PdfRenderer escala la página al tamaño del bitmap de destino
                // cuando la transformación es null.
                page.render(
                    bitmap,
                    null,
                    null,
                    PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY
                )

                page.close()
                bitmap
            }
        }.getOrNull()
    }
}

private fun parsePdfPage(location: String?): Int {
    if (location == null) return 0

    return location
        .substringAfter("page=", "")
        .toIntOrNull()
        ?: 0
}
