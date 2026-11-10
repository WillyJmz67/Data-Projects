package org.openshelf.reader.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "reading_progress")
data class ReadingProgressEntity(
    @PrimaryKey val bookId: String,
    val location: String,
    val page: Int? = null,
    val percent: Float = 0f,
    val updatedAt: Long = System.currentTimeMillis()
)
