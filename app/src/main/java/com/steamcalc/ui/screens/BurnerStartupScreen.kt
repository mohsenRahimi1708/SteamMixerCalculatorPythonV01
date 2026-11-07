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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.steamcalc.domain.BurnerSpec
import com.steamcalc.ui.components.BurnerGrid
import com.steamcalc.ui.components.EChartsView
import com.steamcalc.ui.components.ErrorBanner
import com.steamcalc.ui.components.Metric
import com.steamcalc.ui.components.SectionCard
import com.steamcalc.ui.components.ValueRow
import com.steamcalc.ui.components.WarningList
import com.steamcalc.util.EchartsOptions
import com.steamcalc.util.Units

@Composable
fun BurnerStartupScreen(
    onOpenResults: (String) -> Unit,
    viewModel: BurnerViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var editing by remember { mutableStateOf<BurnerSpec?>(null) }

    val latest = state.latest
    val frames = state.frames
    val chartOption = remember(frames.size, latest?.timeS) {
        if (frames.isEmpty()) {
            EchartsOptions.line(
                title = "Live platen response",
                xName = "s",
                series = emptyList(),
                leftName = Units.TEMPERATURE,
                rightName = Units.POWER,
            )
        } else {
            EchartsOptions.line(
                title = "Live platen response",
                xName = "s",
                series = listOf(
                    EchartsOptions.Series("Outlet T", Units.TEMPERATURE, frames.map { it.timeS }, frames.map { it.tOutC }),
                    EchartsOptions.Series("Metal T", Units.TEMPERATURE, frames.map { it.timeS }, frames.map { it.tMetalC }),
                    EchartsOptions.Series("Gas heat", Units.POWER, frames.map { it.timeS }, frames.map { it.qGasMW }, axisIndex = 1),
                ),
                leftName = Units.TEMPERATURE,
                rightName = Units.POWER,
            )
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Burner start / stop", style = MaterialTheme.typography.titleLarge)
            Text(
                when {
                    state.connected -> "Live"
                    state.connecting -> "Connecting…"
                    else -> "Disconnected"
                },
                style = MaterialTheme.typography.labelLarge,
                color = if (state.connected) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Text(
            "Tap a burner to ignite or shut it down; long press to edit load and ramp time.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = { if (state.connected) viewModel.disconnect() else viewModel.connect() },
                modifier = Modifier.weight(1f),
            ) {
                Text(if (state.connected) "Disconnect" else "Connect")
            }
            OutlinedButton(onClick = { viewModel.saveRun(onOpenResults) }, enabled = frames.isNotEmpty()) {
                Text("Save")
            }
        }

        state.error?.let { ErrorBanner(it) }

        SectionCard(
            title = "Burner grid",
            subtitle = "3 levels × 2 rows × 4 burners · 40 MW each",
        ) {
            BurnerGrid(
                states = state.states,
                onToggle = { viewModel.toggle(it.tag) },
                onEdit = { editing = it },
            )
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedButton(onClick = { viewModel.setAll(true) }) { Text("All ON") }
                OutlinedButton(onClick = { viewModel.setAll(false) }) { Text("All OFF") }
            }
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("A", "B", "C").forEach { level ->
                    OutlinedButton(onClick = { viewModel.setLevel(level) }) { Text("Level $level") }
                }
            }
        }

        SectionCard(title = "Live values", subtitle = "Model time ${Units.withUnit(latest?.timeS, Units.SECONDS, 0)}") {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Metric("Outlet", Units.fmt(latest?.tOutC, 1), Units.TEMPERATURE, emphasis = true)
                Metric("Metal", Units.fmt(latest?.tMetalC, 1), Units.TEMPERATURE, tint = MaterialTheme.colorScheme.secondary)
            }
            Spacer(Modifier.height(8.dp))
            ValueRow("Fired heat", latest?.qBurnersMW, Units.POWER)
            ValueRow("Gas heat to platen", latest?.qGasMW, Units.POWER)
            ValueRow("Heat transfer coefficient", latest?.hWm2k, Units.HTC, 0)
            ValueRow("Reynolds number", latest?.re, "", 0)
            ValueRow("Burners on", latest?.burnersOn?.toDouble(), "", 0)
            Spacer(Modifier.height(6.dp))
            WarningList(latest?.warnings ?: emptyList())
        }

        SectionCard(title = "Live chart", subtitle = "Pinch to zoom · tap legend to combine series") {
            EChartsView(optionJson = chartOption, modifier = Modifier.fillMaxWidth().height(300.dp))
        }

        Text(
            "All values in t/h, °C, bar, MW and W/m²K.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }

    editing?.let { burner ->
        BurnerEditorDialog(
            burner = burner,
            currentLoad = state.states[burner.tag] ?: 0.0,
            onDismiss = { editing = null },
            onApply = { load, ramp ->
                viewModel.configure(burner.tag, load, ramp)
                editing = null
            },
        )
    }
}

@Composable
private fun BurnerEditorDialog(
    burner: BurnerSpec,
    currentLoad: Double,
    onDismiss: () -> Unit,
    onApply: (Double, Double) -> Unit,
) {
    var load by remember { mutableStateOf((currentLoad * 100).toInt().toString()) }
    var ramp by remember { mutableStateOf("30") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Burner ${burner.tag}") },
        text = {
            Column {
                Text(
                    "Level ${burner.level} · ${burner.row} wall · ${Units.withUnit(burner.elevationM, "m", 0)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = load,
                    onValueChange = { load = it },
                    label = { Text("Target load (%)") },
                    singleLine = true,
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = ramp,
                    onValueChange = { ramp = it },
                    label = { Text("Ramp time (s)") },
                    singleLine = true,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val loadValue = (load.toDoubleOrNull() ?: 0.0).coerceIn(0.0, 100.0) / 100.0
                val rampValue = (ramp.toDoubleOrNull() ?: 30.0).coerceIn(0.0, 1800.0)
                onApply(loadValue, rampValue)
            }) { Text("Apply") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Close") } },
    )
}
