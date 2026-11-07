package com.steamcalc.data.api

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.steamcalc.data.settings.SettingsStore
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit

/**
 * Builds Retrofit against the URL currently stored in Settings.
 *
 * The backend address is user editable, so the service is rebuilt whenever the
 * normalised base URL changes; the OkHttp client (connection pool) is shared.
 */
@Singleton
class ApiClient @Inject constructor(
    private val settings: SettingsStore,
    private val okHttpClient: OkHttpClient,
    private val json: Json,
) {
    @Volatile private var cachedBase: String? = null
    @Volatile private var cachedService: ApiService? = null

    fun api(): ApiService {
        val base = normalize(settings.current().backendUrl)
        val existing = cachedService
        if (existing != null && cachedBase == base) return existing
        val service = Retrofit.Builder()
            .baseUrl(base)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ApiService::class.java)
        cachedBase = base
        cachedService = service
        return service
    }

    /** Derive the WebSocket URL for a REST path such as ``ws/burner_startup``. */
    fun webSocketUrl(path: String): String {
        val base = normalize(settings.current().backendUrl)
        val secure = base.startsWith("https://")
        val authority = base.substringAfter("://").trimEnd('/')
        val suffix = if (path.startsWith("/")) path else "/$path"
        return if (secure) "wss://$authority$suffix" else "ws://$authority$suffix"
    }

    /** Normalise user input into a Retrofit-compatible base URL. */
    fun normalize(url: String): String {
        val trimmed = url.trim().ifEmpty { DEFAULT_URL }
        val withScheme = when {
            trimmed.startsWith("http://") || trimmed.startsWith("https://") -> trimmed
            else -> "http://$trimmed"
        }
        return if (withScheme.endsWith("/")) withScheme else "$withScheme/"
    }

    companion object {
        const val DEFAULT_URL = "http://10.0.2.2:8000/"
    }
}
