package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.repository.ApiException
import com.steamcalc.data.repository.RunRepository
import com.steamcalc.data.repository.TwinRepository
import com.steamcalc.data.settings.SettingsStore
import com.steamcalc.domain.SteadyRequest
import com.steamcalc.domain.SteadyResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

/** Editable steady-state form. Values stay as text until validated. */
data class SteadyForm(
    val mMain: String,
    val tMain: String,
    val pMain: String,
    val mSpray: String,
    val tLtOut: String,
    val qPlaten: String,
    val htcMethod: String,
)

sealed interface SteadyStatus {
    data object Idle : SteadyStatus
    data object Running : SteadyStatus
    data object Saved : SteadyStatus
    data class Error(val message: String) : SteadyStatus
}

@HiltViewModel
class SteadyViewModel @Inject constructor(
    private val settings: SettingsStore,
    private val repository: TwinRepository,
    private val runRepository: RunRepository,
    private val json: Json,
) : ViewModel() {

    private val defaults = settings.current()

    private val _form = MutableStateFlow(
        SteadyForm(
            mMain = defaults.mMainTph.toString(),
            tMain = defaults.tMainC.toString(),
            pMain = defaults.pMainBar.toString(),
            mSpray = defaults.mSprayTph.toString(),
            tLtOut = defaults.tLtOutC.toString(),
            qPlaten = defaults.qPlatenMW.toString(),
            htcMethod = defaults.htcMethod,
        ),
    )
    val form: StateFlow<SteadyForm> = _form.asStateFlow()

    private val _result = MutableStateFlow<SteadyResponse?>(null)
    val result: StateFlow<SteadyResponse?> = _result.asStateFlow()

    private val _status = MutableStateFlow<SteadyStatus>(SteadyStatus.Idle)
    val status: StateFlow<SteadyStatus> = _status.asStateFlow()

    fun update(transform: (SteadyForm) -> SteadyForm) {
        _form.value = transform(_form.value)
    }

    fun run() {
        val form = _form.value
        val mMain = form.mMain.toDoubleOrNull()
        val tMain = form.tMain.toDoubleOrNull()
        val pMain = form.pMain.toDoubleOrNull()
        val mSpray = form.mSpray.toDoubleOrNull()
        val tLt = form.tLtOut.toDoubleOrNull()
        val qPlaten = form.qPlaten.toDoubleOrNull()
        if (listOf(mMain, tMain, pMain, mSpray, tLt, qPlaten).any { it == null }) {
            _status.value = SteadyStatus.Error("Fill every field with a number.")
            return
        }
        _status.value = SteadyStatus.Running
        viewModelScope.launch {
            val request = SteadyRequest(
                mMainTph = mMain!!,
                tMainC = tMain!!,
                pMainBar = pMain!!,
                mSprayTph = mSpray!!,
                tLtOutC = tLt!!,
                qPlatenMW = qPlaten!!,
                htcMethod = form.htcMethod,
            )
            repository.steady(request).fold(
                onSuccess = {
                    _result.value = it
                    _status.value = SteadyStatus.Idle
                },
                onFailure = { error ->
                    _status.value = SteadyStatus.Error(
                        (error as? ApiException)?.localized() ?: (error.message ?: "Request failed"),
                    )
                },
            )
        }
    }

    fun save() {
        val result = _result.value ?: return
        val form = _form.value
        viewModelScope.launch {
            val label = "Steady · ${form.mMain} t/h · ${form.tMain} °C"
            runRepository.save(
                kind = "steady",
                label = label,
                tInC = result.tPlatenInC,
                tOutC = result.tPlatenOutC,
                tMetalC = result.tPlatenOutC,
                qPlatenMW = result.heatAbsorbedMW,
                mTph = result.mTotalTph,
                warnings = result.warnings,
                payloadJson = json.encodeToString(SteadyResponse.serializer(), result),
            )
            _status.value = SteadyStatus.Saved
        }
    }
}
