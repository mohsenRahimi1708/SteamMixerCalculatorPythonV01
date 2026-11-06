package com.steamcalc.data.repository

import com.steamcalc.data.db.RunDao
import com.steamcalc.data.db.RunEntity
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow

/** Local Room-backed history of simulation runs. */
@Singleton
class RunRepository @Inject constructor(private val dao: RunDao) {

    val runs: Flow<List<RunEntity>> = dao.observeAll()

    suspend fun get(id: String): RunEntity? = dao.byId(id)

    suspend fun save(
        kind: String,
        label: String,
        tInC: Double,
        tOutC: Double,
        tMetalC: Double,
        qPlatenMW: Double,
        mTph: Double,
        warnings: List<String>,
        payloadJson: String,
    ): String {
        val id = UUID.randomUUID().toString()
        dao.insert(
            RunEntity(
                id = id,
                kind = kind,
                label = label,
                createdAt = System.currentTimeMillis(),
                tInC = tInC,
                tOutC = tOutC,
                tMetalC = tMetalC,
                qPlatenMW = qPlatenMW,
                mTph = mTph,
                warningsCsv = RunEntity.encodeWarnings(warnings),
                payloadJson = payloadJson,
            ),
        )
        return id
    }

    suspend fun delete(id: String) = dao.delete(id)

    suspend fun clear() = dao.clear()
}
