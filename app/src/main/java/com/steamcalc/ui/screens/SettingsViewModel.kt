package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.repository.ApiException
import com.steamcalc.data.repository.TwinRepository
import com.steamcalc.data.settings.AppSettings
import com.steamcalc.data.settings.SettingsStore
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SettingsForm(
    val backendUrl: String,
    val htcMethod: String,
    val mMain: String,
    val tMain: String,
    val pMain: String,
    val mSpray: String,
    val tLtOut: String,
    val qPlaten: String,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settings: SettingsStore,
    private val repository: TwinRepository,
) : ViewModel() {

    private val current = settings.current()
    private val _form = MutableStateFlow(
        SettingsForm(
            backendUrl = current.backendUrl,
            htcMethod = current.htcMethod,
            mMain = current.mMainTph.toString(),
            tMain = current.tMainC.toString(),
            pMain = current.pMainBar.toString(),
            mSpray = current.mSprayTph.toString(),
            tLtOut = current.tLtOutC.toString(),
            qPlaten = current.qPlatenMW.toString(),
        ),
    )
    val form: StateFlow<SettingsForm> = _form.asStateFlow()

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message.asStateFlow()

    fun update(transform: (SettingsForm) -> SettingsForm) {
        _form.value = transform(_form.value)
    }

    fun save() {
        val form = _form.value
        settings.update {
            AppSettings(
                backendUrl = form.backendUrl.trim(),
                htcMethod = form.htcMethod,
                mMainTph = form.mMain.toDoubleOrNull() ?: it.mMainTph,
                tMainC = form.tMain.toDoubleOrNull() ?: it.tMainC,
                pMainBar = form.pMain.toDoubleOrNull() ?: it.pMainBar,
                mSprayTph = form.mSpray.toDoubleOrNull() ?: it.mSprayTph,
                tLtOutC = form.tLtOut.toDoubleOrNull() ?: it.tLtOutC,
                qPlatenMW = form.qPlaten.toDoubleOrNull() ?: it.qPlatenMW,
            )
        }
        _message.value = "Settings saved"
    }

    fun test() {
        save()
        viewModelScope.launch {
            repository.health().fold(
                onSuccess = { _message.value = "Backend reachable · v${it.version}" },
                onFailure = { error ->
                    _message.value = (error as? ApiException)?.localized() ?: "Backend not reachable"
                },
            )
        }
    }
}
