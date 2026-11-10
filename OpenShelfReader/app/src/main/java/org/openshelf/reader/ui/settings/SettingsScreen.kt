package org.openshelf.reader.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.openshelf.reader.BuildConfig
import org.openshelf.reader.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen() {
    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text(stringResource(R.string.settings_title)) })
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(R.string.settings_version, BuildConfig.VERSION_NAME))
            Text(
                stringResource(R.string.settings_privacy),
                modifier = Modifier.padding(top = 8.dp)
            )
        }
    }
}
