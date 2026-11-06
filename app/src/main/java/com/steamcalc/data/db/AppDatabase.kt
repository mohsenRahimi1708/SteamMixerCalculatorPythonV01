package com.steamcalc.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [RunEntity::class], version = 1, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun runDao(): RunDao
}
