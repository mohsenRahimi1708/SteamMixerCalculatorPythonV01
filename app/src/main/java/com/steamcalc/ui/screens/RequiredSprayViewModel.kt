package com.steamcalc.ui.screens

import android.util.Log
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val TAG = "RequiredSprayVM"

data class RequiredSprayUiState(
    val steamFlow: String = "600",
    val steamPressure: String = "167",
    val steamTemp: String = "540",
    val targetTemp: String = "520",
    val sprayTemp: String = "230",
    val initialMetalTemp: String = "540",
    val result: Map<String, Any?>? = null,
    val error: String? = null,
    val isCalculating: Boolean = false
)

class RequiredSprayViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(RequiredSprayUiState())
    val uiState: StateFlow<RequiredSprayUiState> = _uiState.asStateFlow()

    fun update(field: String, value: String) {
        _uiState.update {
            when (field) {
                "steamFlow" -> it.copy(steamFlow = value, error = null, result = null)
                "steamPressure" -> it.copy(steamPressure = value, error = null, result = null)
                "steamTemp" -> it.copy(steamTemp = value, error = null, result = null)
                "targetTemp" -> it.copy(targetTemp = value, error = null, result = null)
                "sprayTemp" -> it.copy(sprayTemp = value, error = null, result = null)
                "initialMetalTemp" -> it.copy(initialMetalTemp = value, error = null, result = null)
                else -> it
            }
        }
    }

    fun calculate() {
        Log.d(TAG, "calculate() called")
        _uiState.update { it.copy(isCalculating = true, error = null, result = null) }
        try {
            val s = _uiState.value
            Log.d(TAG, "Inputs: flow=${s.steamFlow}, P=${s.steamPressure}, T=${s.steamTemp}, target=${s.targetTemp}, spray=${s.sprayTemp}, metal=${s.initialMetalTemp}")
            val result = callEngine(
                "engine", "calculate_required_spray",
                s.steamFlow.toDouble(), s.steamPressure.toDouble(),
                s.steamTemp.toDouble(), s.targetTemp.toDouble(),
                s.sprayTemp.toDouble(), s.initialMetalTemp.toDouble()
            )
            Log.d(TAG, "Result received: $result")

            val status = result["status"]?.toString()
            Log.d(TAG, "Status = $status")
            if (status == "ok") {
                Log.d(TAG, "Setting result in uiState")
                _uiState.update { it.copy(isCalculating = false, result = result) }
                Log.d(TAG, "uiState updated, result=${_uiState.value.result != null}")
            } else {
                val errMsg = result["message"]?.toString() ?: "Unknown error"
                Log.e(TAG, "Engine error: $errMsg")
                _uiState.update {
                    it.copy(isCalculating = false, error = errMsg)
                }
            }
        } catch (e: NumberFormatException) {
            Log.e(TAG, "NumberFormatException", e)
            _uiState.update { it.copy(isCalculating = false, error = "Please enter valid numbers for all fields.") }
        } catch (e: Exception) {
            Log.e(TAG, "Exception: ${e.javaClass.simpleName}: ${e.message}", e)
            _uiState.update { it.copy(isCalculating = false, error = "Engine error: ${e.javaClass.simpleName}: ${e.message}") }
        }
    }
}
