package com.steamcalc.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

/** One saved simulation run (full response kept as JSON for the results screen). */
@Entity(tableName = "runs")
data class RunEntity(
    @PrimaryKey val id: String,
    val kind: String,
    val label: String,
    val createdAt: Long,
    val tInC: Double,
    val tOutC: Double,
    val tMetalC: Double,
    val qPlatenMW: Double,
    val mTph: Double,
    val warningsCsv: String,
    val payloadJson: String,
) {
    val warnings: List<String>
        get() = warningsCsv.split("\u001F").filter { it.isNotBlank() }

    companion object {
        /** Join warnings with a unit separator, which cannot appear in a message. */
        fun encodeWarnings(warnings: List<String>): String =
            warnings.filter { it.isNotBlank() }.joinToString("\u001F")
    }
}
