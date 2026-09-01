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
import com.steamcalc.ui.components.ChartView
import com.steamcalc.ui.components.MetalTempInput
import com.steamcalc.ui.components.SectionHeader

@Composable
fun TransientSimScreen(
    onNavigateToEnergyBalance: (String) -> Unit,
    viewModel: TransientSimViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Transient Simulation", style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Text("Burner ignition — platen thermal inertia",
            style = MaterialTheme.typography.bodySmall, color = Color.Gray,
            modifier = Modifier.padding(bottom = 16.dp))

        // ── Steam Side ───────────────────────────────────────────────
        SectionHeader("Steam Side", MaterialTheme.colorScheme.primary)
        OutlinedTextField(uiState.steamFlow, { viewModel.update("steamFlow", it) },
            label = { Text("Steam flow (t/h)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.steamPressure, { viewModel.update("steamPressure", it) },
            label = { Text("Pressure (bar)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.steamTemp, { viewModel.update("steamTemp", it) },
            label = { Text("Steam inlet temp (°C)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.targetTemp, { viewModel.update("targetTemp", it) },
            label = { Text("Target outlet (°C)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.sprayTemp, { viewModel.update("sprayTemp", it) },
            label = { Text("Spray water temp (°C)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), singleLine = true)

        // ── Initial Metal Temp (mandatory) ───────────────────────────
        MetalTempInput(uiState.initialMetalTemp, { viewModel.update("initialMetalTemp", it) })

        // ── Platen Metal Properties ──────────────────────────────────
        SectionHeader("Platen Metal Properties", Color(0xFF616161))
        OutlinedTextField(uiState.metalMass, { viewModel.update("metalMass", it) },
            label = { Text("Metal mass (kg)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.metalCp, { viewModel.update("metalCp", it) },
            label = { Text("Metal Cp (J/(kg·K))") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), singleLine = true)

        // ── Burner ───────────────────────────────────────────────────
        SectionHeader("Burner", MaterialTheme.colorScheme.tertiary)
        OutlinedTextField(uiState.burnerHeat, { viewModel.update("burnerHeat", it) },
            label = { Text("Heat per burner (MW)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.burnerCount, { viewModel.update("burnerCount", it) },
            label = { Text("Number of burners") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.eta, { viewModel.update("eta", it) },
            label = { Text("η (burner→platen, 0–1)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), singleLine = true)

        // ── Simulation ───────────────────────────────────────────────
        SectionHeader("Simulation", Color(0xFF006A60))
        OutlinedTextField(uiState.timeStep, { viewModel.update("timeStep", it) },
            label = { Text("Time step (s)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), singleLine = true)
        OutlinedTextField(uiState.duration, { viewModel.update("duration", it) },
            label = { Text("Duration (s)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), singleLine = true)

        // ── Simulate Button ──────────────────────────────────────────
        Button(onClick = { viewModel.simulate() },
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
            enabled = !uiState.isSimulating) {
            if (uiState.isSimulating) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp),
                    color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                Spacer(Modifier.width(8.dp))
            }
            Text("RUN SIMULATION", fontWeight = FontWeight.Bold)
        }

        // ── Error Card ───────────────────────────────────────────────
        uiState.error?.let { error ->
            Card(modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer,
                    contentColor = MaterialTheme.colorScheme.onErrorContainer)) {
                Text("⚠ $error", modifier = Modifier.padding(14.dp), style = MaterialTheme.typography.bodyMedium)
            }
        }

        // ── Results ──────────────────────────────────────────────────
        uiState.result?.let { result ->
            @Suppress("UNCHECKED_CAST")
            val steps = result["steps"] as? List<Map<String, Any?>> ?: emptyList()

            Card(modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9),
                    contentColor = Color(0xFF1B5E20))) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text("Simulation Results", style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))

                    Text("Final Metal Temp: ${result["final_metal_temp_c"]} °C",
                        style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold)
                    Text("Final Spray Flow: ${result["final_steady_state_spray_th"]} t/h",
                        style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(bottom = 8.dp))

                    // ── Temperature Chart ────────────────────────────
                    HorizontalDivider(color = Color(0xFFA5D6A7), modifier = Modifier.padding(vertical = 8.dp))
                    if (steps.size >= 2) {
                        val tempData = steps.map { (it["time_s"] as Number).toDouble() to (it["metal_temp_c"] as Number).toDouble() }
                        ChartView(data = tempData, xLabel = "Time (s)", yLabel = "Temp (°C)",
                            lineColor = MaterialTheme.colorScheme.primary, title = "Metal Temperature vs Time",
                            modifier = Modifier.fillMaxWidth().height(220.dp).padding(bottom = 12.dp))
                    }

                    // ── Spray Flow Chart ────────────────────────────
                    if (steps.size >= 2) {
                        val sprayData = steps.map { (it["time_s"] as Number).toDouble() to (it["spray_flow_th"] as Number).toDouble() }
                        ChartView(data = sprayData, xLabel = "Time (s)", yLabel = "Spray (t/h)",
                            lineColor = MaterialTheme.colorScheme.secondary, title = "Spray Flow vs Time",
                            modifier = Modifier.fillMaxWidth().height(180.dp).padding(bottom = 12.dp))
                    }

                    // ── Assumptions ─────────────────────────────────
                    HorizontalDivider(color = Color(0xFFA5D6A7), modifier = Modifier.padding(vertical = 8.dp))
                    Text("Assumptions", style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 4.dp))
                    @Suppress("UNCHECKED_CAST")
                    val a = result["assumptions"] as? Map<String, Any?> ?: emptyMap()
                    Text("Mode: ${a["mode"]}", style = MaterialTheme.typography.bodySmall)
                    Text("Steam: ${a["steam_flow_th"]} t/h, ${a["steam_pressure_bar"]} bar, ${a["steam_temp_c"]} °C", style = MaterialTheme.typography.bodySmall)
                    Text("Target: ${a["target_temp_c"]} °C, Spray: ${a["spray_temp_c"]} °C", style = MaterialTheme.typography.bodySmall)
                    Text("Initial metal temp: ${a["initial_metal_temp_c"]} °C", style = MaterialTheme.typography.bodySmall)
                    Text("Metal: ${a["platen_metal_mass_kg"]} kg, Cp = ${a["metal_cp"]} J/(kg·K)", style = MaterialTheme.typography.bodySmall)
                    Text("Burners: ${a["num_burners"]} × ${a["burner_heat_mw"]} MW, η = ${a["eta"]}", style = MaterialTheme.typography.bodySmall)

                    // ── Warnings ────────────────────────────────────
                    @Suppress("UNCHECKED_CAST")
                    val warnings = result["warnings"] as? List<String> ?: emptyList()
                    if (warnings.isNotEmpty()) {
                        warnings.forEach { w ->
                            Text("⚠ $w", style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFFC62828), modifier = Modifier.padding(bottom = 4.dp))
                        }
                    }

                    // ── Energy Balance ──────────────────────────────
                    HorizontalDivider(color = Color(0xFFA5D6A7), modifier = Modifier.padding(vertical = 8.dp))
                    val lastStep = steps.lastOrNull()
                    OutlinedButton(onClick = {
                        val data = buildString {
                            append("mode=transient")
                            append(";steamFlow=${a["steam_flow_th"]}")
                            append(";steamPressure=${a["steam_pressure_bar"]}")
                            append(";steamTemp=${a["steam_temp_c"]}")
                            append(";targetTemp=${a["target_temp_c"]}")
                            append(";sprayTemp=${a["spray_temp_c"]}")
                            append(";sprayFlow=${lastStep?.get("spray_flow_th")}")
                            append(";initialMetalTemp=${a["initial_metal_temp_c"]}")
                            append(";metalTemp=${lastStep?.get("metal_temp_c")}")
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
