package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.repository.ApiException
import com.steamcalc.data.repository.RunRepository
import com.steamcalc.data.repository.TwinRepository
import com.steamcalc.data.settings.SettingsStore
import com.steamcalc.domain.TransientRequest
import com.steamcalc.domain.TransientResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

data class TransientForm(
    val mMain: String,
    val tMain: String,
    val pMain: String,
    val mSpray: String,
    val tLtOut: String,
    val qPlaten: String,
    val htcMethod: String,
    val durationS: String,
    val dtS: String,
    val initialMode: String,
    val tMetalInit: String,
    val qPlatenInit: String,
)

sealed interface TransientStatus {
    data object Idle : TransientStatus
    data object Running : TransientStatus
    data class Error(val message: String) : TransientStatus
}

@HiltViewModel
class TransientViewModel @Inject constructor(
    private val settings: SettingsStore,
    private val repository: TwinRepository,
    private val runRepository: RunRepository,
    private val json: Json,
) : ViewModel() {

    private val defaults = settings.current()

    private val _form = MutableStateFlow(
        TransientForm(
            mMain = defaults.mMainTph.toString(),
            tMain = defaults.tMainC.toString(),
            pMain = defaults.pMainBar.toString(),
            mSpray = defaults.mSprayTph.toString(),
            tLtOut = defaults.tLtOutC.toString(),
            qPlaten = defaults.qPlatenMW.toString(),
            htcMethod = defaults.htcMethod,
            durationS = "600",
            dtS = "2",
            initialMode = "temperature",
            tMetalInit = "580",
            qPlatenInit = "60",
        ),
    )
    val form: StateFlow<TransientForm> = _form.asStateFlow()

    private val _status = MutableStateFlow<TransientStatus>(TransientStatus.Idle)
    val status: StateFlow<TransientStatus> = _status.asStateFlow()

    private val _savedRunId = MutableStateFlow<String?>(null)
    val savedRunId: StateFlow<String?> = _savedRunId.asStateFlow()

    fun clearSaved() {
        _savedRunId.value = null
    }

    fun update(transform: (TransientForm) -> TransientForm) {
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
        val duration = form.durationS.toDoubleOrNull()
        val dt = form.dtS.toDoubleOrNull()
        if (listOf(mMain, tMain, pMain, mSpray, tLt, qPlaten, duration, dt).any { it == null }) {
            _status.value = TransientStatus.Error("Fill every field with a number.")
            return
        }
        val mode = form.initialMode
        val metal = form.tMetalInit.toDoubleOrNull()
        val qInit = form.qPlatenInit.toDoubleOrNull()
        if (mode == "temperature" && metal == null) {
            _status.value = TransientStatus.Error("Initial metal temperature is required.")
            return
        }
        if (mode == "heat_flux" && qInit == null) {
            _status.value = TransientStatus.Error("Initial heat input is required.")
            return
        }
        _status.value = TransientStatus.Running
        viewModelScope.launch {
            val previousId = if (mode == "previous_run") {
                repository.serverRuns(1).getOrNull()?.firstOrNull()?.id
            } else {
                null
            }
            if (mode == "previous_run" && previousId == null) {
                _status.value = TransientStatus.Error("No stored run is available on the backend.")
                return@launch
            }
            val request = TransientRequest(
                mMainTph = mMain!!,
                tMainC = tMain!!,
                pMainBar = pMain!!,
                mSprayTph = mSpray!!,
                tLtOutC = tLt!!,
                qPlatenMW = qPlaten!!,
                htcMethod = form.htcMethod,
                durationS = duration!!,
                dtS = dt!!,
                initialMode = mode,
                tMetalInitC = if (mode == "temperature") metal else null,
                qPlatenInitMW = if (mode == "heat_flux") qInit else null,
                previousRunId = previousId,
            )
            repository.transient(request).fold(
                onSuccess = { response ->
                    val id = persist(response, form)
                    _savedRunId.value = id
                    _status.value = TransientStatus.Idle
                },
                onFailure = { error ->
                    _status.value = TransientStatus.Error(
                        (error as? ApiException)?.localized() ?: (error.message ?: "Request failed"),
                    )
                },
            )
        }
    }

    private suspend fun persist(response: TransientResponse, form: TransientForm): String {
        val tOutLast = response.tOutC.lastOrNull() ?: 0.0
        val tMetalLast = response.tMetalC.lastOrNull() ?: 0.0
        val tIn = response.tInC.firstOrNull() ?: 0.0
        return runRepository.save(
            kind = "transient",
            label = "Transient · ${form.durationS} s · ${form.initialMode}",
            tInC = tIn,
            tOutC = tOutLast,
            tMetalC = tMetalLast,
            qPlatenMW = response.qGasMW.lastOrNull() ?: 0.0,
            mTph = response.mTotalTph,
            warnings = response.warnings,
            payloadJson = json.encodeToString(TransientResponse.serializer(), response),
        )
    }
}
