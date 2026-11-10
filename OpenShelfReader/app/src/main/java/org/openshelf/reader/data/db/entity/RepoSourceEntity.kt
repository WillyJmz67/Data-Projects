package org.openshelf.reader.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "repo_sources")
data class RepoSourceEntity(
    @PrimaryKey val id: String,
    val owner: String,
    val repo: String,
    val branch: String = "main",
    val addedAt: Long = System.currentTimeMillis(),
    val enabled: Boolean = true
)
