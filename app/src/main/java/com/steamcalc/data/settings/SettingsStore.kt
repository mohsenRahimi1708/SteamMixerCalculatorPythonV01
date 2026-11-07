package com.steamcalc.data.settings

import android.content.Context
import com.steamcalc.BuildConfig
import com.steamcalc.data.api.ApiClient
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** User settings, persisted in SharedPreferences. */
data class AppSettings(
    val backendUrl: String = ApiClient.DEFAULT_URL,
    val htcMethod: String = "gnielinski",
    val mMainTph: Double = 1000.0,
    val tMainC: Double = 540.0,
    val pMainBar: Double = 167.0,
    val mSprayTph: Double = 0.0,
    val tLtOutC: Double = 490.0,
    val qPlatenMW: Double = 60.0,
)

/** Observable settings storage backed by SharedPreferences. */
@Singleton
class SettingsStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val _state = MutableStateFlow(read())
    val state: StateFlow<AppSettings> = _state.asStateFlow()

    fun current(): AppSettings = _state.value

    fun update(transform: (AppSettings) -> AppSettings) {
        val next = transform(_state.value)
        _state.value = next
        prefs.edit()
            .putString(KEY_URL, next.backendUrl)
            .putString(KEY_HTC, next.htcMethod)
            .putString(KEY_M_MAIN, next.mMainTph.toString())
            .putString(KEY_T_MAIN, next.tMainC.toString())
            .putString(KEY_P_MAIN, next.pMainBar.toString())
            .putString(KEY_M_SPRAY, next.mSprayTph.toString())
            .putString(KEY_T_LT, next.tLtOutC.toString())
            .putString(KEY_Q_PLATEN, next.qPlatenMW.toString())
            .apply()
    }

    private fun read(): AppSettings {
        val defaults = AppSettings(
            backendUrl = if (BuildConfig.DEFAULT_BACKEND_URL.isNotBlank()) {
                BuildConfig.DEFAULT_BACKEND_URL
            } else {
                ApiClient.DEFAULT_URL
            },
        )
        return AppSettings(
            backendUrl = prefs.getString(KEY_URL, defaults.backendUrl) ?: defaults.backendUrl,
            htcMethod = prefs.getString(KEY_HTC, defaults.htcMethod) ?: defaults.htcMethod,
            mMainTph = prefs.getString(KEY_M_MAIN, null)?.toDoubleOrNull() ?: defaults.mMainTph,
            tMainC = prefs.getString(KEY_T_MAIN, null)?.toDoubleOrNull() ?: defaults.tMainC,
            pMainBar = prefs.getString(KEY_P_MAIN, null)?.toDoubleOrNull() ?: defaults.pMainBar,
            mSprayTph = prefs.getString(KEY_M_SPRAY, null)?.toDoubleOrNull() ?: defaults.mSprayTph,
            tLtOutC = prefs.getString(KEY_T_LT, null)?.toDoubleOrNull() ?: defaults.tLtOutC,
            qPlatenMW = prefs.getString(KEY_Q_PLATEN, null)?.toDoubleOrNull() ?: defaults.qPlatenMW,
        )
    }

    private companion object {
        const val PREFS = "platen_settings"
        const val KEY_URL = "backend_url"
        const val KEY_HTC = "htc_method"
        const val KEY_M_MAIN = "m_main"
        const val KEY_T_MAIN = "t_main"
        const val KEY_P_MAIN = "p_main"
        const val KEY_M_SPRAY = "m_spray"
        const val KEY_T_LT = "t_lt"
        const val KEY_Q_PLATEN = "q_platen"
    }
}
