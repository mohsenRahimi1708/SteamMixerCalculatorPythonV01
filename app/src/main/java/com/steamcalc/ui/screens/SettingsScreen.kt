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
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.steamcalc.ui.components.NumberField
import com.steamcalc.ui.components.SectionCard
import com.steamcalc.util.Units

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = hiltViewModel()) {
    val form by viewModel.form.collectAsStateWithLifecycle()
    val message by viewModel.message.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Settings", style = MaterialTheme.typography.titleLarge)

        SectionCard(title = "Backend", subtitle = "Use the plant server address, e.g. https://platen.plant.local/") {
            OutlinedTextField(
                value = form.backendUrl,
                onValueChange = { value -> viewModel.update { it.copy(backendUrl = value) } },
                label = { Text("Backend URL") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            Spacer(Modifier.height(10.dp))
            Text("Default correlation", style = MaterialTheme.typography.labelLarge)
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

        SectionCard(title = "Default parameters", subtitle = "Pre-filled on every new run") {
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
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { viewModel.save() }, modifier = Modifier.weight(1f)) {
                Text("Save settings")
            }
            OutlinedButton(onClick = { viewModel.test() }) {
                Text("Test connection")
            }
        }

        message?.let {
            Text(
                it,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.secondary,
            )
        }
    }
}
