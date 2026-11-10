package org.openshelf.reader.ui.repositories

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import org.openshelf.reader.R
import org.openshelf.reader.domain.model.RepoSource

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RepositoriesScreen(
    onOpenCatalog: (String) -> Unit,
    viewModel: RepositoriesViewModel = viewModel()
) {
    val repos by viewModel.repos.collectAsStateWithLifecycle()
    var input by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text(stringResource(R.string.repositories_title)) })

        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.repositories_help))
            OutlinedTextField(
                value = input,
                onValueChange = { input = it },
                label = { Text(stringResource(R.string.repositories_field_label)) },
                modifier = Modifier.fillMaxWidth()
            )
            Button(
                onClick = {
                    viewModel.addRepo(input)
                    input = ""
                },
                enabled = input.isNotBlank()
            ) { Text(stringResource(R.string.repositories_add)) }
        }

        LazyColumn {
            items(repos, key = { it.id }) { repo ->
                RepoRow(
                    repo = repo,
                    onOpenCatalog = { onOpenCatalog(repo.id) },
                    onDelete = { viewModel.remove(repo.id) }
                )
            }
        }
    }
}

@Composable
private fun RepoRow(
    repo: RepoSource,
    onOpenCatalog: () -> Unit,
    onDelete: () -> Unit
) {
    ListItem(
        headlineContent = { Text("${repo.owner}/${repo.repo}") },
        supportingContent = {
            Text(stringResource(R.string.repositories_branch, repo.branch))
        },
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp),
        trailingContent = {
            Row {
                Button(onClick = onOpenCatalog) {
                    Text(stringResource(R.string.repositories_view_books))
                }
                IconButton(onClick = onDelete) {
                    Icon(
                        Icons.Filled.Delete,
                        contentDescription = stringResource(R.string.repositories_delete)
                    )
                }
            }
        }
    )
}
