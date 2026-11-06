package com.steamcalc.data.repository

import com.steamcalc.data.api.ApiClient
import com.steamcalc.domain.ApiErrorDetail
import com.steamcalc.domain.ApiErrorEnvelope
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
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import retrofit2.HttpException

/** Bilingual failure surfaced to the UI. */
class ApiException(
    val code: String,
    val messageEn: String,
    val messageFa: String,
) : Exception(messageEn) {
    /** Pick the locale-appropriate text, falling back to English. */
    fun localized(): String {
        val persian = Locale.getDefault().language == "fa"
        return if (persian && messageFa.isNotBlank()) messageFa else messageEn
    }
}

/** Single entry point for every backend call, with uniform error handling. */
@Singleton
class TwinRepository @Inject constructor(
    private val apiClient: ApiClient,
    private val json: Json,
) {
    suspend fun steady(body: SteadyRequest): Result<SteadyResponse> =
        call { apiClient.api().steady(body) }

    suspend fun transient(body: TransientRequest): Result<TransientResponse> =
        call { apiClient.api().transient(body) }

    suspend fun burnerStartup(body: BurnerStartupRequest): Result<BurnerStartupResponse> =
        call { apiClient.api().burnerStartup(body) }

    suspend fun htc(pBar: Double, tC: Double, mTph: Double, method: String): Result<HtcResponse> =
        call { apiClient.api().htc(pBar = pBar, tC = tC, mTph = mTph, method = method) }

    suspend fun properties(pBar: Double, tC: Double): Result<PropertiesResponse> =
        call { apiClient.api().properties(pBar, tC) }

    suspend fun burners(): Result<List<BurnerSpec>> = call { apiClient.api().burners() }

    suspend fun presets(): Result<List<BurnerPreset>> = call { apiClient.api().presets() }

    suspend fun serverRuns(limit: Int = 30): Result<List<RunSummary>> =
        call { apiClient.api().runs(limit) }

    suspend fun saveServerRun(body: RunCreate): Result<RunDetail> =
        call { apiClient.api().saveRun(body) }

    suspend fun health(): Result<HealthResponse> = call { apiClient.api().health() }

    private suspend fun <T> call(block: suspend () -> T): Result<T> = try {
        Result.success(block())
    } catch (error: HttpException) {
        Result.failure(parseHttpError(error))
    } catch (error: Exception) {
        Result.failure(
            ApiException(
                code = "network_error",
                messageEn = error.message ?: "Cannot reach the backend.",
                messageFa = "ارتباط با سرور برقرار نشد.",
            ),
        )
    }

    private fun parseHttpError(error: HttpException): ApiException {
        val body = runCatching { error.response()?.errorBody()?.string() }.getOrNull()
        val detail: ApiErrorDetail? = body?.let {
            runCatching { json.decodeFromString(ApiErrorEnvelope.serializer(), it).detail }.getOrNull()
        }
        return ApiException(
            code = detail?.code ?: "http_${error.code()}",
            messageEn = detail?.messageEn?.takeIf { it.isNotBlank() }
                ?: "Request failed with HTTP ${error.code()}.",
            messageFa = detail?.messageFa?.takeIf { it.isNotBlank() }
                ?: "درخواست با خطای ${error.code()} ناموفق بود.",
        )
    }
}
