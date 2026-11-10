package org.openshelf.reader.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow
import org.openshelf.reader.data.db.entity.RepoSourceEntity

@Dao
interface RepoSourceDao {

    @Query("SELECT * FROM repo_sources ORDER BY addedAt DESC")
    fun observeAll(): Flow<List<RepoSourceEntity>>

    @Query("SELECT * FROM repo_sources WHERE id = :id")
    suspend fun findById(id: String): RepoSourceEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(repo: RepoSourceEntity)

    @Query("DELETE FROM repo_sources WHERE id = :id")
    suspend fun deleteById(id: String)
}
