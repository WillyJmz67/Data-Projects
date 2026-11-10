package org.openshelf.reader.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "books")
data class BookEntity(
    @PrimaryKey val id: String,
    val title: String,
    val author: String? = null,
    val format: String,
    val localPath: String? = null,
    val remoteUrl: String? = null,
    val coverPath: String? = null,
    val collectionName: String? = null,
    val language: String? = null,
    val repoId: String? = null,
    val addedAt: Long = System.currentTimeMillis(),
    val lastReadAt: Long? = null,
    val progressPercent: Float = 0f,
    val progressLocation: String? = null,
    val isFavorite: Boolean = false
)
