package com.steamcalc.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.steamcalc.ui.components.ErrorBanner
import com.steamcalc.ui.components.NumberField
import com.steamcalc.ui.components.SectionCard
import com.steamcalc.util.Units

@Composable
fun TransientScreen(
    onOpenResults: (String) -> Unit,
    viewModel: TransientViewModel = hiltViewModel(),
) {
    val form by viewModel.form.collectAsStateWithLifecycle()
    val status by viewModel.status.collectAsStateWithLifecycle()
    val savedRunId by viewModel.savedRunId.collectAsStateWithLifecycle()

    LaunchedEffect(savedRunId) {
        savedRunId?.let {
            onOpenResults(it)
            viewModel.clearSaved()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Transient run", style = MaterialTheme.typography.titleLarge)
        Text(
            "Single-node metal model with a dynamic heat transfer coefficient.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        SectionCard(title = "Operating point") {
            NumberField("Main steam flow", form.mMain, Units.FLOW, { v -> viewModel.update { it.copy(mMain = v) } })
            Spacer(Modifier.height(8.dp))
            NumberField("Main steam temperature", form.tMain, Units.TEMPERATURE, { v -> viewModel.update { it.copy(tMain = v) } })
            Spacer(Modifier.height(8.dp))
            NumberField("Main steam pressure", form.pMain, Units.PRESSURE, { v -> viewModel.update { it.copy(pMain = v) } })
            Spacer(Modifier.height(8.dp))
            NumberField("First-stage spray flow", form.mSpray, Units.FLOW, { v -> viewModel.update { it.copy(mSpray = v) } })
            Spacer(Modifier.height(8.dp))
            NumberField("LT superheater outlet temperature", form.tLtOut, Units.TEMPERATURE, { v -> viewModel.update { it.copy(tLtOut = v) } })
            Spacer(Modifier.height(8.dp))
            NumberField("Platen heat absorption", form.qPlaten, Units.POWER, { v -> viewModel.update { it.copy(qPlaten = v) } })
            Spacer(Modifier.height(10.dp))
            Text("Heat transfer correlation", style = MaterialTheme.typography.labelLarge)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("gnielinski", "dittus_boelter").forEach { method ->
                    FilterChip(
                        selected = form.htcMethod == method,
                        onClick = { viewModel.update { it.copy(htcMethod = method) } },
                        label = { Text(method) },
                    )
                }
            }
        }

        SectionCard(title = "Time stepping") {
            NumberField("Duration", form.durationS, Units.SECONDS, { v -> viewModel.update { it.copy(durationS = v) } })
            Spacer(Modifier.height(8.dp))
            NumberField("Time step", form.dtS, Units.SECONDS, { v -> viewModel.update { it.copy(dtS = v) } })
        }

        SectionCard(title = "Initial condition", subtitle = "The solver validates the state physics.") {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("temperature", "heat_flux", "previous_run").forEach { mode ->
                    FilterChip(
                        selected = form.initialMode == mode,
                        onClick = { viewModel.update { it.copy(initialMode = mode) } },
                        label = { Text(mode) },
                    )
                }
            }
            Spacer(Modifier.height(10.dp))
            if (form.initialMode == "temperature") {
                NumberField("Initial metal temperature", form.tMetalInit, Units.TEMPERATURE, { v ->
                    viewModel.update { it.copy(tMetalInit = v) }
                })
            }
            if (form.initialMode == "heat_flux") {
                NumberField("Initial heat input", form.qPlatenInit, Units.POWER, { v ->
                    viewModel.update { it.copy(qPlatenInit = v) }
                })
            }
            if (form.initialMode == "previous_run") {
                Text(
                    "The most recent run stored on the backend is used.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        Button(
            onClick = { viewModel.run() },
            enabled = status !is TransientStatus.Running,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (status is TransientStatus.Running) {
                CircularProgressIndicator(modifier = Modifier.height(18.dp), strokeWidth = 2.dp)
            } else {
                Text("Run and open results")
            }
        }

        (status as? TransientStatus.Error)?.let { ErrorBanner(it.message) }

        Text(
            "All values in t/h, °C, bar, MW and W/m²K.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
