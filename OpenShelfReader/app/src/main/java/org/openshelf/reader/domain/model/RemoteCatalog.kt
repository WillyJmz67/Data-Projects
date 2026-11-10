package org.openshelf.reader.domain.model

import kotlinx.serialization.Serializable

@Serializable
data class RemoteCatalog(
    val name: String? = null,
    val description: String? = null,
    val books: List<RemoteBook> = emptyList()
)

@Serializable
data class RemoteBook(
    val id: String,
    val title: String,
    val author: String? = null,
    val file: String,
    val cover: String? = null,
    val type: String? = null,
    val collection: String? = null,
    val language: String? = null,
    val description: String? = null,
    val readingDirection: String? = null
)
