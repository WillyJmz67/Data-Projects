package org.openshelf.reader.domain.model

data class Book(
    val id: String,
    val title: String,
    val author: String?,
    val format: BookFormat,
    val localPath: String?,
    val remoteUrl: String?,
    val coverPath: String?,
    val collection: String?,
    val language: String?,
    val repoId: String?,
    val addedAt: Long,
    val lastReadAt: Long?,
    val progressPercent: Float,
    val isFavorite: Boolean
)
