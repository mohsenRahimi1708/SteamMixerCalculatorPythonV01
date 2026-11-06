package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.api.WsClient
import com.steamcalc.data.repository.ApiException
import com.steamcalc.data.repository.RunRepository
import com.steamcalc.data.settings.SettingsStore
import com.steamcalc.domain.BurnerLayout
import com.steamcalc.domain.BurnerStartupRequest
import com.steamcalc.domain.BurnerStartupResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.WebSocket

/** One streamed frame of the live burner simulation, in API units. */
data class LiveFrame(
    val timeS: Double,
    val tInC: Double,
    val tOutC: Double,
    val tMetalC: Double,
    val qBurnersMW: Double,
    val qGasMW: Double,
    val hWm2k: Double,
    val re: Double,
    val nu: Double,
    val regime: String,
    val burnersOn: Int,
    val states: Map<String, Double>,
    val warnings: List<String>,
)

data class BurnerUiState(
    val connected: Boolean = false,
    val connecting: Boolean = false,
    val error: String? = null,
    val frames: List<LiveFrame> = emptyList(),
    val states: Map<String, Double> = emptyMap(),
    val latest: LiveFrame? = null,
    val message: String? = null,
    val lastSavedId: String? = null,
)

@HiltViewModel
class BurnerViewModel @Inject constructor(
    private val wsClient: WsClient,
    private val settings: SettingsStore,
    private val runRepository: RunRepository,
    private val json: Json,
) : ViewModel() {

    private val _state = MutableStateFlow(BurnerUiState(states = emptyMap()))
    val state: StateFlow<BurnerUiState> = _state.asStateFlow()

    private var socket: WebSocket? = null
    private var pendingRequest: BurnerStartupRequest? = null
    private var lastFrameAt: Long = 0L
    private val frameCap = 600

    fun connect() {
        if (_state.value.connecting || _state.value.connected) return
        val current = settings.current()
        val request = BurnerStartupRequest(
            mMainTph = current.mMainTph,
            tMainC = current.tMainC,
            pMainBar = current.pMainBar,
            mSprayTph = current.mSprayTph,
            tLtOutC = current.tLtOutC,
            qPlatenMW = current.qPlatenMW,
            htcMethod = current.htcMethod,
            durationS = 7200.0,
            dtS = 0.5,
            initialMode = "heat_flux",
            qPlatenInitMW = 1.0,
        )
        pendingRequest = request
        _state.value = _state.value.copy(connecting = true, error = null, message = null, frames = emptyList())
        socket = wsClient.connect(
            path = "ws/burner_startup",
            onMessage = { frame -> handle(frame) },
            onClosed = { reason ->
                _state.value = _state.value.copy(
                    connected = false,
                    connecting = false,
                    message = reason ?: _state.value.message,
                )
            },
        )
        socket?.send(wsClient.startBurner(request, speed = 1.0).toString())
    }

    fun disconnect() {
        socket?.send(wsClient.stop().toString())
        socket?.close(1000, "client disconnect")
        socket = null
        _state.value = _state.value.copy(connected = false, connecting = false)
    }

    fun reconnect() {
        disconnect()
        connect()
    }

    fun toggle(tag: String) {
        val load = _state.value.states[tag] ?: 0.0
        sendBurner(tag, if (load > 0.01) "off" else "on", if (load > 0.01) 0.0 else 1.0, 30.0)
    }

    fun setAll(on: Boolean) {
        BurnerLayout.burners.forEach { burner ->
            sendBurner(burner.tag, if (on) "on" else "off", if (on) 1.0 else 0.0, 30.0)
        }
    }

    fun setLevel(level: String) {
        BurnerLayout.burners.forEach { burner ->
            val on = burner.level == level
            sendBurner(burner.tag, if (on) "on" else "off", if (on) 1.0 else 0.0, 30.0)
        }
    }

    fun configure(tag: String, load: Double, rampS: Double) {
        val state = if (load > 0.01) "on" else "off"
        sendBurner(tag, state, load, rampS)
    }

    private fun sendBurner(tag: String, state: String, load: Double, rampS: Double) {
        if (!_state.value.connected && !_state.value.connecting) return
        socket?.send(wsClient.setBurner(tag, state, load, rampS).toString())
    }

    private fun handle(message: JsonObject) {
        when (message["type"]?.jsonPrimitive?.contentOrNull) {
            "ready" -> {
                _state.value = _state.value.copy(connected = true, connecting = false, error = null)
            }

            "frame" -> {
                val frame = parseFrame(message) ?: return
                val frames = (_state.value.frames + frame).takeLast(frameCap)
                lastFrameAt = System.currentTimeMillis()
                _state.value = _state.value.copy(
                    frames = frames,
                    latest = frame,
                    states = frame.states,
                    message = null,
                )
            }

            "event_ack" -> {
                val tag = message["event"]?.let { it as? JsonObject }
                    ?.get("tag")?.jsonPrimitive?.contentOrNull
                _state.value = _state.value.copy(message = tag?.let { "Command acknowledged: $it" })
            }

            "error" -> {
                _state.value = _state.value.copy(
                    error = message["message"]?.jsonPrimitive?.contentOrNull ?: "Stream error",
                )
            }

            "done" -> {
                _state.value = _state.value.copy(connected = false, connecting = false)
            }
        }
    }

    private fun parseFrame(message: JsonObject): LiveFrame? {
        fun value(key: String): Double =
            (message[key] as? JsonPrimitive)?.doubleOrNull ?: 0.0

        val states = buildMap {
            (message["burner_states"] as? JsonObject)?.forEach { (tag, element) ->
                (element as? JsonPrimitive)?.doubleOrNull?.let { put(tag, it) }
            }
        }
        val warnings = (message["warnings"] as? JsonArray)
            ?.mapNotNull { (it as? JsonPrimitive)?.contentOrNull }
            ?: emptyList()
        return LiveFrame(
            timeS = value("time_s"),
            tInC = value("T_in_C"),
            tOutC = value("T_out_C"),
            tMetalC = value("T_metal_C"),
            qBurnersMW = value("Q_burners_MW"),
            qGasMW = value("Q_gas_MW"),
            hWm2k = value("h_W_m2K"),
            re = value("Re"),
            nu = value("Nu"),
            regime = message["regime"]?.jsonPrimitive?.contentOrNull ?: "",
            burnersOn = (message["burners_on"] as? JsonPrimitive)?.doubleOrNull?.toInt() ?: 0,
            states = states,
            warnings = warnings,
        )
    }

    /** Freeze the live session into the local history. */
    fun saveRun(onSaved: (String) -> Unit) {
        val frames = _state.value.frames
        if (frames.isEmpty()) return
        viewModelScope.launch {
            val payload = BurnerStartupResponse(
                timeS = frames.map { it.timeS },
                tOutC = frames.map { it.tOutC },
                tMetalC = frames.map { it.tMetalC },
                tInC = frames.map { it.tInC },
                qGasMW = frames.map { it.qGasMW },
                qBurnersMW = frames.map { it.qBurnersMW },
                hWm2k = frames.map { it.hWm2k },
                Re = frames.map { it.re },
                Nu = frames.map { it.nu },
                regime = frames.map { it.regime },
                warnings = frames.lastOrNull()?.warnings ?: emptyList(),
                burnerStatesFinal = frames.lastOrNull()?.states ?: emptyMap(),
            )
            val id = runRepository.save(
                kind = "burner_startup",
                label = "Burner session · ${frames.size} frames",
                tInC = frames.first().tInC,
                tOutC = frames.last().tOutC,
                tMetalC = frames.last().tMetalC,
                qPlatenMW = frames.last().qGasMW,
                mTph = pendingRequest?.mMainTph ?: 0.0,
                warnings = frames.lastOrNull()?.warnings ?: emptyList(),
                payloadJson = json.encodeToString(BurnerStartupResponse.serializer(), payload),
            )
            _state.value = _state.value.copy(lastSavedId = id)
            onSaved(id)
        }
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }

    override fun onCleared() {
        socket?.close(1000, "view model cleared")
        super.onCleared()
    }
}
