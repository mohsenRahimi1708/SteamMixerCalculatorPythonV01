package com.steamcalc.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.steamcalc.data.db.RunEntity
import com.steamcalc.data.repository.RunRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val runRepository: RunRepository,
) : ViewModel() {

    val runs: StateFlow<List<RunEntity>> = runRepository.runs.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = emptyList(),
    )

    fun delete(id: String) {
        viewModelScope.launch { runRepository.delete(id) }
    }
}
