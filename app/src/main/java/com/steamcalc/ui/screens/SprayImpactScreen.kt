package com.steamcalc.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.steamcalc.ui.components.MetalTempInput
import com.steamcalc.ui.components.SectionHeader

@Composable
fun SprayImpactScreen(
    onNavigateToEnergyBalance: (String) -> Unit,
    viewModel: SprayImpactViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)
    ) {
        Text("Spray Impact (Mode B)", style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Text("Forward: given spray flow → resulting temperature",
            style = MaterialTheme.typography.bodySmall, color = Color.Gray,
            modifier = Modifier.padding(bottom = 16.dp))

        // ── Steam Inlet ──────────────────────────────────────────────
        SectionHeader("Steam Inlet", MaterialTheme.colorScheme.primary)
        OutlinedTextField(uiState.steamFlow, { viewModel.update("steamFlow", it) },
            label = { Text("Steam mass flow (t/h)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.steamPressure, { viewModel.update("steamPressure", it) },
            label = { Text("Steam pressure (bar)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.steamTemp, { viewModel.update("steamTemp", it) },
            label = { Text("Steam temperature (°C)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), singleLine = true)

        // ── Spray Water ──────────────────────────────────────────────
        SectionHeader("Spray Water", MaterialTheme.colorScheme.secondary)
        OutlinedTextField(uiState.sprayFlow, { viewModel.update("sprayFlow", it) },
            label = { Text("Spray flow (t/h)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.sprayTemp, { viewModel.update("sprayTemp", it) },
            label = { Text("Spray water temperature (°C)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), singleLine = true)

        // ── Initial Metal Temp (mandatory) ───────────────────────────
        MetalTempInput(uiState.initialMetalTemp, { viewModel.update("initialMetalTemp", it) })

        // ── Calculate Button ─────────────────────────────────────────
        Button(onClick = { viewModel.calculate() },
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
            enabled = !uiState.isCalculating) {
            if (uiState.isCalculating) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp),
                    color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                Spacer(Modifier.width(8.dp))
            }
            Text("CALCULATE", fontWeight = FontWeight.Bold)
        }

        // ── Error Card ───────────────────────────────────────────────
        uiState.error?.let { error ->
            Card(modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer,
                    contentColor = MaterialTheme.colorScheme.onErrorContainer)) {
                Text("⚠ $error", modifier = Modifier.padding(14.dp),
                    style = MaterialTheme.typography.bodyMedium)
            }
        }

        // ── Results ──────────────────────────────────────────────────
        uiState.result?.let { result ->
            Card(modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE3F2FD),
                    contentColor = Color(0xFF0D47A1))) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Results — Spray Impact", style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))

                    Text("Outlet Temperature: ${result["outlet_temp_c"]} °C",
                        style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold,
                        color = Color(0xFF1565C0), modifier = Modifier.padding(bottom = 4.dp))
                    Text("Temperature Drop: ${result["temperature_drop_c"]} °C",
                        style = MaterialTheme.typography.bodyLarge)
                    Text("Combined Flow: ${result["combined_flow_th"]} t/h",
                        style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(bottom = 8.dp))

                    HorizontalDivider(color = Color(0xFF90CAF9), modifier = Modifier.padding(vertical = 8.dp))
                    Text("Enthalpy Chain", style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 4.dp))
                    Text("h_steam(P,T): ${result["h_steam"]} kJ/kg", style = MaterialTheme.typography.bodySmall)
                    Text("h_spray(P,T): ${result["h_spray"]} kJ/kg", style = MaterialTheme.typography.bodySmall)
                    Text("h_out(mix): ${result["h_out"]} kJ/kg", style = MaterialTheme.typography.bodySmall)

                    // Assumptions
                    HorizontalDivider(color = Color(0xFF90CAF9), modifier = Modifier.padding(vertical = 8.dp))
                    Text("Assumptions", style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 4.dp))
                    @Suppress("UNCHECKED_CAST")
                    val assumptions = result["assumptions"] as? Map<String, Any?> ?: emptyMap()
                    Text("Mode: ${assumptions["mode"]}", style = MaterialTheme.typography.bodySmall)
                    Text("Steam: ${assumptions["steam_flow_th"]} t/h, ${assumptions["steam_pressure_bar"]} bar, ${assumptions["steam_temp_c"]} °C", style = MaterialTheme.typography.bodySmall)
                    Text("Spray: ${assumptions["spray_flow_th"]} t/h, ${assumptions["spray_temp_c"]} °C", style = MaterialTheme.typography.bodySmall)
                    Text("Initial metal temp: ${assumptions["initial_metal_temp_c"]} °C", style = MaterialTheme.typography.bodySmall)

                    // Warnings
                    @Suppress("UNCHECKED_CAST")
                    val warnings = result["warnings"] as? List<String> ?: emptyList()
                    if (warnings.isNotEmpty()) {
                        HorizontalDivider(color = Color(0xFF90CAF9), modifier = Modifier.padding(vertical = 8.dp))
                        warnings.forEach { w ->
                            Text("⚠ $w", style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFFC62828), modifier = Modifier.padding(bottom = 4.dp))
                        }
                    }

                    // Energy Balance button
                    HorizontalDivider(color = Color(0xFF90CAF9), modifier = Modifier.padding(vertical = 8.dp))
                    OutlinedButton(onClick = {
                        val data = buildString {
                            append("mode=B")
                            append(";steamFlow=${assumptions["steam_flow_th"]}")
                            append(";steamPressure=${assumptions["steam_pressure_bar"]}")
                            append(";steamTemp=${assumptions["steam_temp_c"]}")
                            append(";sprayTemp=${assumptions["spray_temp_c"]}")
                            append(";sprayFlow=${assumptions["spray_flow_th"]}")
                            append(";hSteam=${result["h_steam"]}")
                            append(";hSpray=${result["h_spray"]}")
                            append(";hOut=${result["h_out"]}")
                            append(";outletTemp=${result["outlet_temp_c"]}")
                            append(";initialMetalTemp=${assumptions["initial_metal_temp_c"]}")
                        }
                        onNavigateToEnergyBalance(data)
                    }, modifier = Modifier.fillMaxWidth()) {
                        Text("View Full Energy Balance", style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
    }
}
