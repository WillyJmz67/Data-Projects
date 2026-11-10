package org.openshelf.reader.ui.reader

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import org.openshelf.reader.R
import org.openshelf.reader.domain.model.BookFormat
import org.openshelf.reader.ui.cbz.CbzReaderScreen
import org.openshelf.reader.ui.epub.EpubReaderScreen
import org.openshelf.reader.ui.pdf.PdfReaderScreen
import org.openshelf.reader.ui.theme.OpenShelfTheme

/**
 * Actividad del lector. Decide qué lector abrir según el formato del libro.
 */
class ReaderActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val bookId = intent.getStringExtra("book_id")
        val bookPath = intent.getStringExtra("book_path")

        if (bookId == null || bookPath == null) {
            finish()
            return
        }

        setContent {
            OpenShelfTheme {
                ReaderRoot(
                    bookId = bookId,
                    bookPath = bookPath,
                    onBack = { finish() }
                )
            }
        }
    }
}

@Composable
private fun ReaderRoot(
    bookId: String,
    bookPath: String,
    onBack: () -> Unit
) {
    val format = BookFormat.fromFileName(bookPath)

    when (format) {
        BookFormat.EPUB -> {
            EpubReaderScreen(
                bookId = bookId,
                filePath = bookPath,
                onBack = onBack
            )
        }

        BookFormat.PDF -> {
            PdfReaderScreen(
                bookId = bookId,
                filePath = bookPath,
                onBack = onBack
            )
        }

        BookFormat.CBZ -> {
            CbzReaderScreen(
                bookId = bookId,
                filePath = bookPath,
                onBack = onBack
            )
        }

        else -> {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text(stringResource(R.string.reader_unsupported))
            }
        }
    }
}
