package org.openshelf.reader.ui.cbz

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import org.openshelf.reader.util.naturalCompare
import java.util.zip.ZipEntry
import java.util.zip.ZipFile

private data class CbzLoadedState(
    val zipFile: ZipFile,
    val entries: List<ZipEntry>,
    val initialPage: Int
)

/**
 * Lector de cómics/manga CBZ:
 * - Extrae las imágenes del ZIP en orden natural de páginas.
 * - Soporta modo manga derecha-a-izquierda (RTL).
 * - Soporta doble página.
 * - Zoom con pellizco en cada página.
 * - Recuerda página, modo RTL y doble página por libro.
 */
@Composable
fun CbzReaderScreen(
    bookId: String,
    filePath: String,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val app = context.applicationContext as OpenShelfApp
    val repository = app.container.libraryRepository

    var state by remember { mutableStateOf<CbzLoadedState?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    var rtl by remember { mutableStateOf(false) }
    var doublePage by remember { mutableStateOf(false) }

    LaunchedEffect(filePath) {
        val progress = repository.getProgress(bookId)
        val parsed = parseCbzLocation(progress?.location)

        val result = withContext(Dispatchers.IO) {
            runCatching {
                val zip = ZipFile(filePath)

                val entries = zip.entries().asSequence()
                    .filter { !it.isDirectory }
                    .filter { entry ->
                        val name = entry.name.lowercase()
                        name.endsWith(".jpg") ||
                            name.endsWith(".jpeg") ||
                            name.endsWith(".png") ||
                            name.endsWith(".webp") ||
                            name.endsWith(".gif") ||
                            name.endsWith(".bmp")
                    }
                    .sortedWith { a, b -> naturalCompare(a.name, b.name) }
                    .toList()

                if (entries.isEmpty()) {
                    zip.close()
                    error("empty")
                }

                CbzLoadedState(
                    zipFile = zip,
                    entries = entries,
                    initialPage = parsed.first.coerceIn(0, (entries.size - 1).coerceAtLeast(0))
                )
            }
        }

        result.fold(
            onSuccess = {
                state = it
                rtl = parsed.second
                doublePage = parsed.third
            },
            onFailure = {
                errorMessage = context.getString(R.string.reader_open_cbz_error)
            }
        )
    }

    DisposableEffect(state) {
        onDispose {
            state?.zipFile?.let {
                runCatching { it.close() }
            }
        }
    }

    val loaded = state

    if (errorMessage != null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(errorMessage ?: "", modifier = Modifier.padding(32.dp))
        }
        return
    }

    if (loaded == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    val pageCount = if (doublePage) {
        (loaded.entries.size + 1) / 2
    } else {
        loaded.entries.size
    }

    if (pageCount == 0) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(stringResource(R.string.reader_no_images))
        }
        return
    }

    val pagerState = rememberPagerState(
        initialPage = loaded.initialPage.let {
            if (doublePage) it / 2 else it
        },
        pageCount = { pageCount }
    )

    val mutex = remember { Mutex() }

    // Guardar progreso: página actual + modos
    LaunchedEffect(pagerState, rtl, doublePage) {
        snapshotFlow { pagerState.currentPage }
            .collect { page ->
                val percent = if (pageCount <= 1) {
                    1f
                } else {
                    page.toFloat() / (pageCount - 1)
                }

                repository.saveProgress(
                    bookId = bookId,
                    location = "cbz:page=$page;rtl=$rtl;double=$doublePage",
                    percent = percent
                )
            }
    }

    Box(Modifier.fillMaxSize()) {
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxSize(),
            reverseLayout = rtl
        ) { page ->
            if (doublePage) {
                val firstIndex = page * 2
                val secondIndex = firstIndex + 1

                val first = loaded.entries.getOrNull(firstIndex)
                val second = loaded.entries.getOrNull(secondIndex)

                val pages = if (rtl) {
                    listOfNotNull(second, first)
                } else {
                    listOfNotNull(first, second)
                }

                if (pages.isEmpty()) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(stringResource(R.string.reader_no_images))
                    }
                } else {
                    Row(
                        modifier = Modifier.fillMaxSize(),
                        horizontalArrangement = Arrangement.Center
                    ) {
                        pages.forEach { entry ->
                            CbzPageImage(
                                zipFile = loaded.zipFile,
                                mutex = mutex,
                                entry = entry,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            } else {
                val entry = loaded.entries.getOrNull(page)

                if (entry != null) {
                    CbzPageImage(
                        zipFile = loaded.zipFile,
                        mutex = mutex,
                        entry = entry,
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(stringResource(R.string.reader_no_images))
                    }
                }
            }
        }

        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(12.dp)
        ) {
            TextButton(onClick = { rtl = !rtl }) {
                Text(
                    if (rtl) stringResource(R.string.reader_manga_rtl)
                    else stringResource(R.string.reader_manga_ltr)
                )
            }

            TextButton(onClick = { doublePage = !doublePage }) {
                Text(
                    if (doublePage) stringResource(R.string.reader_double_on)
                    else stringResource(R.string.reader_double_off)
                )
            }
        }
    }
}

@Composable
private fun CbzPageImage(
    zipFile: ZipFile,
    mutex: Mutex,
    entry: ZipEntry,
    modifier: Modifier = Modifier
) {
    BoxWithConstraints(modifier) {
        val width = if (constraints.maxWidth > 0) constraints.maxWidth else 1080
        val height = if (constraints.maxHeight > 0) constraints.maxHeight else 1920

        var bitmap by remember(entry) {
            mutableStateOf<Bitmap?>(null)
        }
        var isError by remember(entry) {
            mutableStateOf(false)
        }

        LaunchedEffect(entry) {
            val bmp = withContext(Dispatchers.IO) {
                mutex.withLock {
                    decodeZipImage(
                        zipFile = zipFile,
                        entry = entry,
                        reqWidth = width,
                        reqHeight = height
                    )
                }
            }
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
                isError -> Text(stringResource(R.string.reader_no_images))
                else -> CircularProgressIndicator()
            }
        }
    }
}

private fun decodeZipImage(
    zipFile: ZipFile,
    entry: ZipEntry,
    reqWidth: Int,
    reqHeight: Int
): Bitmap? {
    return runCatching {
        val bounds = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }

        zipFile.getInputStream(entry).use { input ->
            BitmapFactory.decodeStream(input, null, bounds)
        }

        val options = BitmapFactory.Options().apply {
            inJustDecodeBounds = false
            inSampleSize = calculateInSampleSize(bounds, reqWidth, reqHeight)
        }

        zipFile.getInputStream(entry).use { input ->
            BitmapFactory.decodeStream(input, null, options)
        }
    }.getOrNull()
}

private fun calculateInSampleSize(
    options: BitmapFactory.Options,
    reqWidth: Int,
    reqHeight: Int
): Int {
    val height = options.outHeight
    val width = options.outWidth

    var inSampleSize = 1

    if (height > reqHeight || width > reqWidth) {
        val halfHeight = height / 2
        val halfWidth = width / 2

        while (halfHeight / inSampleSize >= reqHeight && halfWidth / inSampleSize >= reqWidth) {
            inSampleSize *= 2
        }
    }

    return inSampleSize
}

private fun parseCbzLocation(location: String?): Triple<Int, Boolean, Boolean> {
    if (location == null) return Triple(0, false, false)

    val page = location
        .substringAfter("page=", "")
        .substringBefore(";")
        .toIntOrNull()
        ?: 0

    val rtl = location.contains("rtl=true")
    val double = location.contains("double=true")

    return Triple(page, rtl, double)
}
