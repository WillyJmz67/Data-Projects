package org.openshelf.reader.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import coil.compose.AsyncImage
import java.io.File

@Composable
fun BookCover(
    coverPath: String?,
    contentDescription: String,
    modifier: Modifier = Modifier
) {
    val file = coverPath?.let { File(it) }
    if (file != null && file.exists()) {
        AsyncImage(
            model = file,
            contentDescription = contentDescription,
            contentScale = ContentScale.Crop,
            modifier = modifier
        )
    } else {
        Box(
            modifier = modifier.background(MaterialTheme.colorScheme.surfaceVariant),
            contentAlignment = Alignment.Center
        ) {
            Text(contentDescription.take(2).uppercase())
        }
    }
}
