package com.steamcalc.data.api

import com.steamcalc.domain.BurnerPreset
import com.steamcalc.domain.BurnerSpec
import com.steamcalc.domain.BurnerStartupRequest
import com.steamcalc.domain.BurnerStartupResponse
import com.steamcalc.domain.HealthResponse
import com.steamcalc.domain.HtcResponse
import com.steamcalc.domain.PropertiesResponse
import com.steamcalc.domain.RunCreate
import com.steamcalc.domain.RunDetail
import com.steamcalc.domain.RunSummary
import com.steamcalc.domain.SteadyRequest
import com.steamcalc.domain.SteadyResponse
import com.steamcalc.domain.TransientRequest
import com.steamcalc.domain.TransientResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/** REST contract of the Python backend; every payload uses t/h, °C, bar, MW, W/m²K. */
interface ApiService {

    @POST("api/steady")
    suspend fun steady(@Body body: SteadyRequest): SteadyResponse

    @POST("api/transient")
    suspend fun transient(@Body body: TransientRequest): TransientResponse

    @POST("api/burner_startup")
    suspend fun burnerStartup(@Body body: BurnerStartupRequest): BurnerStartupResponse

    @GET("api/htc")
    suspend fun htc(
        @Query("P_bar") pBar: Double,
        @Query("T_C") tC: Double,
        @Query("m_tph") mTph: Double,
        @Query("tubes") tubes: Int = 172,
        @Query("method") method: String = "gnielinski",
    ): HtcResponse

    @GET("api/properties")
    suspend fun properties(
        @Query("P_bar") pBar: Double,
        @Query("T_C") tC: Double,
    ): PropertiesResponse

    @GET("api/burners")
    suspend fun burners(): List<BurnerSpec>

    @GET("api/burner_presets")
    suspend fun presets(): List<BurnerPreset>

    @GET("api/runs")
    suspend fun runs(@Query("limit") limit: Int = 30): List<RunSummary>

    @POST("api/runs")
    suspend fun saveRun(@Body body: RunCreate): RunDetail

    @GET("api/health")
    suspend fun health(): HealthResponse
}
