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
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
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
import com.steamcalc.util.Units
import com.steamcalc.ui.components.Metric
import com.steamcalc.ui.components.SectionCard
import com.steamcalc.ui.components.ValueRow

@Composable
fun HomeScreen(
    onNavigate: (String) -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val runs by viewModel.runs.collectAsStateWithLifecycle()
    val backend by viewModel.backend.collectAsStateWithLifecycle()
    val latest = runs.firstOrNull()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Platen superheater", style = MaterialTheme.typography.titleLarge)
        Text(
            "325 MW unit · 1000 t/h · 167 bar · 540 °C",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        SectionCard(
            title = "Latest saved run",
            subtitle = latest?.label ?: "No saved runs yet",
        ) {
            if (latest == null) {
                Text(
                    "Run a steady-state prediction first.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Metric(
                        label = "Outlet",
                        value = Units.fmt(latest.tOutC, 1),
                        unit = Units.TEMPERATURE,
                        emphasis = true,
                    )
                    Metric(
                        label = "Metal",
                        value = Units.fmt(latest.tMetalC, 1),
                        unit = Units.TEMPERATURE,
                        tint = MaterialTheme.colorScheme.secondary,
                    )
                }
                Spacer(Modifier.height(8.dp))
                ValueRow("Inlet temperature", latest.tInC, Units.TEMPERATURE)
                ValueRow("Absorbed heat", latest.qPlatenMW, Units.POWER)
                ValueRow("Steam flow", latest.mTph, Units.FLOW)
                Spacer(Modifier.height(8.dp))
                OutlinedButton(onClick = { onNavigate("results/${latest.id}") }) {
                    Text("Open results")
                }
            }
        }

        SectionCard(title = "Backend", subtitle = "Streaming and REST endpoint") {
            when (val state = backend) {
                is BackendState.Online -> Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    AssistChip(onClick = { viewModel.refreshBackend() }, label = { Text("Online") })
                    Text(
                        "v${state.version}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                is BackendState.Offline -> AssistChip(
                    onClick = { viewModel.refreshBackend() },
                    label = { Text("Offline · tap to retry") },
                )

                BackendState.Unknown -> AssistChip(
                    onClick = { viewModel.refreshBackend() },
                    label = { Text("Checking…") },
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(
                "All values in t/h, °C, bar, MW and W/m²K.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { onNavigate("steady") }, modifier = Modifier.weight(1f)) {
                Text("Steady run")
            }
            OutlinedButton(onClick = { onNavigate("burner") }, modifier = Modifier.weight(1f)) {
                Text("Burners")
            }
        }
    }
}
