package com.steamcalc.data.api

import com.steamcalc.domain.BurnerStartupRequest
import com.steamcalc.domain.TransientRequest
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.encodeToJsonElement
import kotlinx.serialization.json.put
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

/**
 * WebSocket transport for the streaming simulation endpoints.
 *
 * Receives decoded JSON frames and forwards them to the caller; reconnection
 * and frame aggregation live in the burner view model.
 */
@Singleton
class WsClient @Inject constructor(
    private val apiClient: ApiClient,
    private val okHttpClient: OkHttpClient,
    private val json: Json,
) {
    fun connect(
        path: String,
        onMessage: (JsonObject) -> Unit,
        onClosed: (String?) -> Unit,
    ): WebSocket {
        val request = Request.Builder().url(apiClient.webSocketUrl(path)).build()
        val listener = object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                runCatching { json.parseToJsonElement(text) as JsonObject }
                    .onSuccess(onMessage)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onClosed(t.message ?: "connection failed")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                onClosed(reason.ifEmpty { null })
            }
        }
        return okHttpClient.newWebSocket(request, listener)
    }

    fun startTransient(request: TransientRequest, speed: Double = 10.0): JsonObject =
        buildJsonObject {
            put("type", "start")
            put("speed", speed)
            put("request", json.encodeToJsonElement(TransientRequest.serializer(), request))
        }

    fun startBurner(request: BurnerStartupRequest, speed: Double = 1.0): JsonObject =
        buildJsonObject {
            put("type", "start")
            put("speed", speed)
            put("request", json.encodeToJsonElement(BurnerStartupRequest.serializer(), request))
        }

    fun setBurner(tag: String, state: String, load: Double, rampS: Double): JsonObject =
        buildJsonObject {
            put("action", "set_burner")
            put("tag", tag)
            put("state", state)
            put("target_load_fraction", load)
            put("ramp_time_s", rampS)
        }

    fun stop(): JsonObject = buildJsonObject { put("type", "stop") }
}
