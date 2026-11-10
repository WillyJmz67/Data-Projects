package org.openshelf.reader.data.db

import androidx.room.Database
import androidx.room.RoomDatabase
import org.openshelf.reader.data.db.dao.BookDao
import org.openshelf.reader.data.db.dao.ProgressDao
import org.openshelf.reader.data.db.dao.RepoSourceDao
import org.openshelf.reader.data.db.entity.BookEntity
import org.openshelf.reader.data.db.entity.ReadingProgressEntity
import org.openshelf.reader.data.db.entity.RepoSourceEntity

@Database(
    entities = [
        BookEntity::class,
        ReadingProgressEntity::class,
        RepoSourceEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class OpenShelfDatabase : RoomDatabase() {
    abstract fun bookDao(): BookDao
    abstract fun progressDao(): ProgressDao
    abstract fun repoSourceDao(): RepoSourceDao
}
