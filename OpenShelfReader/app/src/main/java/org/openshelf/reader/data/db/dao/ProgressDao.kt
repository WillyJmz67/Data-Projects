package org.openshelf.reader.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import org.openshelf.reader.data.db.entity.ReadingProgressEntity

@Dao
interface ProgressDao {

    @Query("SELECT * FROM reading_progress WHERE bookId = :bookId")
    suspend fun forBook(bookId: String): ReadingProgressEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(progress: ReadingProgressEntity)
}
