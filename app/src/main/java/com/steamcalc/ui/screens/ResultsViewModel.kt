package com.steamcalc.ui.screens

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.db.RunEntity
import com.steamcalc.data.repository.RunRepository
import com.steamcalc.util.EchartsOptions
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
import kotlinx.serialization.json.doubleOrNull

/** One plotted quantity of a saved run. */
data class ChartSeries(
    val key: String,
    val label: String,
    val unit: String,
    val axis: Int,
    val x: List<Double>,
    val y: List<Double>,
)

/** CSV export description. */
data class ExportPayload(
    val fileName: String,
    val header: List<String>,
    val rows: List<List<String>>,
)

@HiltViewModel
class ResultsViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val runRepository: RunRepository,
    private val json: Json,
) : ViewModel() {

    private val runId: String = savedStateHandle.get<String>("runId").orEmpty()

    private val _run = MutableStateFlow<RunEntity?>(null)
    val run: StateFlow<RunEntity?> = _run.asStateFlow()

    private val _series = MutableStateFlow<List<ChartSeries>>(emptyList())
    val series: StateFlow<List<ChartSeries>> = _series.asStateFlow()

    private val _selected = MutableStateFlow<Set<String>>(emptySet())
    val selected: StateFlow<Set<String>> = _selected.asStateFlow()

    private val _summary = MutableStateFlow<List<Pair<String, String>>>(emptyList())
    val summary: StateFlow<List<Pair<String, String>>> = _summary.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _captureToken = MutableStateFlow(0)
    val captureToken: StateFlow<Int> = _captureToken.asStateFlow()

    private var optionCache: String = EchartsOptionsPlaceholder
    private val chartCache = mutableMapOf<Set<String>, String>()

    init {
        load()
    }

    private fun load() {
        viewModelScope.launch {
            val entity = runRepository.get(runId)
            if (entity == null) {
                _error.value = "This run is not stored on this device."
                return@launch
            }
            _run.value = entity
            val payload = runCatching {
                json.parseToJsonElement(entity.payloadJson) as JsonObject
            }.getOrNull()
            if (payload == null) {
                _error.value = "Stored payload is not valid JSON."
                return@launch
            }
            parseSeries(payload)
            parseSummary(payload)
        }
    }

    private fun parseSeries(payload: JsonObject) {
        val time = payload.list("time_s")
        if (time.isEmpty()) {
            _series.value = emptyList()
            return
        }
        val candidates = listOf(
            Triple("T_out_C", "Outlet T", "°C") to 0,
            Triple("T_metal_C", "Metal T", "°C") to 0,
            Triple("T_in_C", "Inlet T", "°C") to 0,
            Triple("Q_gas_MW", "Gas heat", "MW") to 1,
            Triple("Q_burners_MW", "Fired heat", "MW") to 1,
            Triple("Q_steam_MW", "Heat to steam", "MW") to 1,
            Triple("h_W_m2K", "h", "W/m²K") to 1,
            Triple("Re", "Re", "") to 1,
            Triple("Nu", "Nu", "") to 1,
        )
        val built = candidates.mapNotNull { (meta, axis) ->
            val (key, label, unit) = meta
            val values = payload.list(key)
            if (values.size != time.size || values.isEmpty()) return@mapNotNull null
            ChartSeries(key = key, label = label, unit = unit, axis = axis, x = time, y = values)
        }
        _series.value = built
        val defaults = built.map { it.key }.filter { it == "T_out_C" || it == "T_metal_C" }.toSet()
        _selected.value = if (defaults.isEmpty()) built.take(2).map { it.key }.toSet() else defaults
        chartCache.clear()
    }

    private fun parseSummary(payload: JsonObject) {
        val rows = mutableListOf<Pair<String, String>>()
        fun add(key: String, label: String, unit: String, decimals: Int = 1) {
            val value = (payload[key] as? JsonPrimitive)?.doubleOrNull ?: return
            rows += label to format(value, unit, decimals)
        }
        add("T_platen_in_C", "Platen inlet", "°C", 2)
        add("T_platen_out_C", "Platen outlet", "°C", 2)
        add("deltaT_spray_C", "Spray drop", "°C", 2)
        add("heat_absorbed_MW", "Absorbed heat", "MW", 1)
        add("h_W_m2K", "Heat transfer coefficient", "W/m²K", 0)
        add("tau_s", "Time constant τ", "s", 0)
        add("t63_s", "t63", "s", 0)
        add("t95_s", "t95", "s", 0)
        add("q_platen_fraction", "Platen heat fraction", "", 2)
        add("gas_to_metal_lag_s", "Gas transport delay", "s", 1)
        add("t_reach_T_out_s", "Target outlet reached at", "s", 0)
        add("Re", "Reynolds number", "", 0)
        add("Nu", "Nusselt number", "", 1)
        _summary.value = rows
    }

    private fun format(value: Double, unit: String, decimals: Int): String {
        val number = com.steamcalc.util.Units.fmt(value, decimals)
        return if (unit.isBlank()) number else "$number $unit"
    }

    fun toggle(key: String) {
        val current = _selected.value
        _selected.value = if (current.contains(key)) current - key else current + key
    }

    fun chartOption(): String {
        val selectedNow = _selected.value
        chartCache[selectedNow]?.let { return it }
        val active = _series.value.filter { selectedNow.contains(it.key) }
        val run = _run.value
        val option = if (active.isEmpty()) {
            EchartsOptions.line(
                title = run?.label ?: "Results",
                xName = "s",
                series = emptyList(),
                leftName = "°C",
                rightName = "MW",
            )
        } else {
            EchartsOptions.line(
                title = run?.label ?: "Results",
                xName = "s",
                series = active.map {
                    EchartsOptions.Series(it.label, it.unit, it.x, it.y, it.axis)
                },
                leftName = "°C",
                rightName = "MW · W/m²K",
            )
        }
        chartCache[selectedNow] = option
        optionCache = option
        return option
    }

    fun csvPayload(): ExportPayload? {
        val run = _run.value ?: return null
        if (_series.value.isEmpty()) {
            val header = listOf("Quantity", "Value")
            val rows = _summary.value.map { listOf(it.first, it.second) }
            return ExportPayload("platen-${run.id.take(8)}.csv", header, rows)
        }
        val active = _series.value.filter { _selected.value.contains(it.key) }
        val time = active.firstOrNull()?.x ?: return null
        val header = buildList {
            add("time (s)")
            active.forEach { add("${it.label} (${it.unit})") }
        }
        val rows = time.indices.map { index ->
            buildList {
                add(com.steamcalc.util.Units.fmt(time[index], 3))
                active.forEach { series ->
                    add(com.steamcalc.util.Units.fmt(series.y.getOrNull(index), 4))
                }
            }
        }
        return ExportPayload("platen-${run.id.take(8)}.csv", header, rows)
    }

    fun requestPng() {
        _captureToken.value += 1
    }

    private fun JsonObject.list(key: String): List<Double> =
        (this[key] as? JsonArray)?.mapNotNull { (it as? JsonPrimitive)?.doubleOrNull } ?: emptyList()

    private companion object {
        const val EchartsOptionsPlaceholder = ""
    }
}
