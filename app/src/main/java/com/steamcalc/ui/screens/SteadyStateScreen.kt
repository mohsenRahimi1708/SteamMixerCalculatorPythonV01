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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.steamcalc.ui.components.ErrorBanner
import com.steamcalc.ui.components.NumberField
import com.steamcalc.ui.components.SectionCard
import com.steamcalc.ui.components.ValueRow
import com.steamcalc.ui.components.WarningList
import com.steamcalc.util.Units

@Composable
fun SteadyStateScreen(viewModel: SteadyViewModel = hiltViewModel()) {
    val form by viewModel.form.collectAsStateWithLifecycle()
    val result by viewModel.result.collectAsStateWithLifecycle()
    val status by viewModel.status.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Steady-state prediction", style = MaterialTheme.typography.titleLarge)
        Text(
            "IF97 enthalpy balance across the platen with the tube-side heat transfer coefficient.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        SectionCard(title = "Inputs") {
            NumberField("Main steam flow", form.mMain, Units.FLOW, { v ->
                viewModel.update { it.copy(mMain = v) }
            })
            Spacer(Modifier.height(8.dp))
            NumberField("Main steam temperature", form.tMain, Units.TEMPERATURE, { v ->
                viewModel.update { it.copy(tMain = v) }
            })
            Spacer(Modifier.height(8.dp))
            NumberField("Main steam pressure", form.pMain, Units.PRESSURE, { v ->
                viewModel.update { it.copy(pMain = v) }
            })
            Spacer(Modifier.height(8.dp))
            NumberField("First-stage spray flow", form.mSpray, Units.FLOW, { v ->
                viewModel.update { it.copy(mSpray = v) }
            })
            Spacer(Modifier.height(8.dp))
            NumberField("LT superheater outlet temperature", form.tLtOut, Units.TEMPERATURE, { v ->
                viewModel.update { it.copy(tLtOut = v) }
            })
            Spacer(Modifier.height(8.dp))
            NumberField("Platen heat absorption", form.qPlaten, Units.POWER, { v ->
                viewModel.update { it.copy(qPlaten = v) }
            })
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

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = { viewModel.run() },
                enabled = status !is SteadyStatus.Running,
                modifier = Modifier.weight(1f),
            ) {
                if (status is SteadyStatus.Running) {
                    CircularProgressIndicator(modifier = Modifier.height(18.dp), strokeWidth = 2.dp)
                } else {
                    Text("Run")
                }
            }
            OutlinedButton(onClick = { viewModel.save() }, enabled = result != null) {
                Text("Save run")
            }
        }

        when (val state = status) {
            is SteadyStatus.Error -> ErrorBanner(state.message)
            SteadyStatus.Saved -> Text(
                "Saved to history.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.secondary,
            )
            else -> Unit
        }

        result?.let { steady ->
            SectionCard(title = "Prediction", subtitle = "${form.htcMethod} · ${steady.regime}") {
                ValueRow("Platen inlet", steady.tPlatenInC, Units.TEMPERATURE, 2)
                ValueRow("Platen outlet", steady.tPlatenOutC, Units.TEMPERATURE, 2)
                ValueRow("Spray temperature drop", steady.deltaTSprayC, Units.TEMPERATURE, 2)
                ValueRow("Absorbed heat", steady.heatAbsorbedMW, Units.POWER)
                ValueRow("Heat transfer coefficient", steady.hWm2k, Units.HTC, 0)
                ValueRow("Reynolds number", steady.Re, "", 0)
                ValueRow("Nusselt number", steady.Nu, "", 1)
                ValueRow("Mixed enthalpy", steady.hMixKjKg, "kJ/kg", 1)
                Spacer(Modifier.height(6.dp))
                WarningList(steady.warnings)
            }
        }

        Text(
            "All values in t/h, °C, bar, MW and W/m²K.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.align(Alignment.CenterHorizontally),
        )
    }
}
