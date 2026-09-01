package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class TransientSimUiState(
    val steamFlow: String = "600",
    val steamPressure: String = "167",
    val steamTemp: String = "540",
    val targetTemp: String = "520",
    val sprayTemp: String = "230",
    val initialMetalTemp: String = "540",
    val metalMass: String = "62600",
    val metalCp: String = "500",
    val burnerHeat: String = "40",
    val burnerCount: String = "4",
    val eta: String = "0.07",
    val timeStep: String = "10",
    val duration: String = "600",
    val result: Map<String, Any?>? = null,
    val error: String? = null,
    val isSimulating: Boolean = false
)

class TransientSimViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(TransientSimUiState())
    val uiState: StateFlow<TransientSimUiState> = _uiState.asStateFlow()

    fun update(field: String, value: String) {
        _uiState.update {
            when (field) {
                "steamFlow" -> it.copy(steamFlow = value, error = null, result = null)
                "steamPressure" -> it.copy(steamPressure = value, error = null, result = null)
                "steamTemp" -> it.copy(steamTemp = value, error = null, result = null)
                "targetTemp" -> it.copy(targetTemp = value, error = null, result = null)
                "sprayTemp" -> it.copy(sprayTemp = value, error = null, result = null)
                "initialMetalTemp" -> it.copy(initialMetalTemp = value, error = null, result = null)
                "metalMass" -> it.copy(metalMass = value, error = null, result = null)
                "metalCp" -> it.copy(metalCp = value, error = null, result = null)
                "burnerHeat" -> it.copy(burnerHeat = value, error = null, result = null)
                "burnerCount" -> it.copy(burnerCount = value, error = null, result = null)
                "eta" -> it.copy(eta = value, error = null, result = null)
                "timeStep" -> it.copy(timeStep = value, error = null, result = null)
                "duration" -> it.copy(duration = value, error = null, result = null)
                else -> it
            }
        }
    }

    fun simulate() {
        _uiState.update { it.copy(isSimulating = true, error = null, result = null) }
        try {
            val s = _uiState.value
            val result = callEngine(
                "engine", "run_transient_simulation",
                s.steamFlow.toDouble(), s.steamPressure.toDouble(),
                s.steamTemp.toDouble(), s.targetTemp.toDouble(),
                s.sprayTemp.toDouble(), s.initialMetalTemp.toDouble(),
                s.metalMass.toDouble(), s.metalCp.toDouble(),
                s.burnerHeat.toDouble(), s.burnerCount.toInt(), s.eta.toDouble(),
                s.timeStep.toDouble(), s.duration.toDouble()
            )

            val status = result["status"]?.toString()
            if (status == "ok") {
                _uiState.update { it.copy(isSimulating = false, result = result) }
            } else {
                _uiState.update {
                    it.copy(isSimulating = false, error = result["message"]?.toString() ?: "Unknown error")
                }
            }
        } catch (e: NumberFormatException) {
            _uiState.update { it.copy(isSimulating = false, error = "Please enter valid numbers for all fields.") }
        } catch (e: Exception) {
            _uiState.update { it.copy(isSimulating = false, error = "Simulation error: ${e.message}") }
        }
    }
}
