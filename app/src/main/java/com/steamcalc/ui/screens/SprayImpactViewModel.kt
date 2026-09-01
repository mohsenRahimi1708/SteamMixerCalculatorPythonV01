package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class SprayImpactUiState(
    val steamFlow: String = "600",
    val steamPressure: String = "167",
    val steamTemp: String = "540",
    val sprayFlow: String = "10",
    val sprayTemp: String = "230",
    val initialMetalTemp: String = "540",
    val result: Map<String, Any?>? = null,
    val error: String? = null,
    val isCalculating: Boolean = false
)

class SprayImpactViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(SprayImpactUiState())
    val uiState: StateFlow<SprayImpactUiState> = _uiState.asStateFlow()

    fun update(field: String, value: String) {
        _uiState.update {
            when (field) {
                "steamFlow" -> it.copy(steamFlow = value, error = null, result = null)
                "steamPressure" -> it.copy(steamPressure = value, error = null, result = null)
                "steamTemp" -> it.copy(steamTemp = value, error = null, result = null)
                "sprayFlow" -> it.copy(sprayFlow = value, error = null, result = null)
                "sprayTemp" -> it.copy(sprayTemp = value, error = null, result = null)
                "initialMetalTemp" -> it.copy(initialMetalTemp = value, error = null, result = null)
                else -> it
            }
        }
    }

    fun calculate() {
        _uiState.update { it.copy(isCalculating = true, error = null, result = null) }
        try {
            val s = _uiState.value
            val result = callEngine(
                "engine", "calculate_spray_impact",
                s.steamFlow.toDouble(), s.steamPressure.toDouble(),
                s.steamTemp.toDouble(), s.sprayFlow.toDouble(),
                s.sprayTemp.toDouble(), s.initialMetalTemp.toDouble()
            )

            val status = result["status"]?.toString()
            if (status == "ok") {
                _uiState.update { it.copy(isCalculating = false, result = result) }
            } else {
                _uiState.update {
                    it.copy(isCalculating = false, error = result["message"]?.toString() ?: "Unknown error")
                }
            }
        } catch (e: NumberFormatException) {
            _uiState.update { it.copy(isCalculating = false, error = "Please enter valid numbers for all fields.") }
        } catch (e: Exception) {
            _uiState.update { it.copy(isCalculating = false, error = "Engine error: ${e.message}") }
        }
    }
}
