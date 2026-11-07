package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.db.RunEntity
import com.steamcalc.data.repository.RunRepository
import com.steamcalc.data.repository.TwinRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/** Backend reachability for the dashboard badge. */
sealed interface BackendState {
    data object Unknown : BackendState
    data class Online(val version: String) : BackendState
    data class Offline(val message: String) : BackendState
}

@HiltViewModel
class HomeViewModel @Inject constructor(
    runRepository: RunRepository,
    private val twinRepository: TwinRepository,
) : ViewModel() {

    val runs: StateFlow<List<RunEntity>> = runRepository.runs.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = emptyList(),
    )

    private val _backend = MutableStateFlow<BackendState>(BackendState.Unknown)
    val backend: StateFlow<BackendState> = _backend.asStateFlow()

    init {
        refreshBackend()
    }

    fun refreshBackend() {
        viewModelScope.launch {
            twinRepository.health().fold(
                onSuccess = { _backend.value = BackendState.Online(it.version) },
                onFailure = { _backend.value = BackendState.Offline(it.message ?: "offline") },
            )
        }
    }
}
