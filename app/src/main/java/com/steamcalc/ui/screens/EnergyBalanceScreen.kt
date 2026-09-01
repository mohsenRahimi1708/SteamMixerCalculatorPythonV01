package com.steamcalc.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.net.URLDecoder

@Composable
fun EnergyBalanceScreen(data: String, onBack: () -> Unit) {
    val params = remember(data) { parseEnergyBalanceData(data) }

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
        Text("Energy Balance Report", style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(bottom = 4.dp))

        val modeLabel = when (params.mode) {
            "A" -> "Mode A — Required Spray (Steady-State)"
            "B" -> "Mode B — Spray Impact (Forward)"
            "transient" -> "Transient Simulation"
            else -> "Unknown Mode"
        }
        Text(modeLabel, style = MaterialTheme.typography.bodySmall, color = Color.Gray,
            modifier = Modifier.padding(bottom = 16.dp))

        // ── Input Conditions ─────────────────────────────────────────
        ReportSection("INPUT CONDITIONS") {
            ReportLine("Steam flow", "${fmt(params.steamFlow)} t/h")
            ReportLine("Steam pressure", "${fmt(params.steamPressure)} bar")
            ReportLine("Steam inlet temp", "${fmt(params.steamTemp)} °C")
            if (params.mode != "B") ReportLine("Target outlet", "${fmt(params.targetTemp)} °C")
            ReportLine("Spray water temp", "${fmt(params.sprayTemp)} °C")
            ReportLine("Spray flow", "${fmt(params.sprayFlow)} t/h")
            ReportLine("Initial metal temp", "${fmt(params.initialMetalTemp)} °C")
        }

        // ── Enthalpies ───────────────────────────────────────────────
        ReportSection("STEAM-SIDE ENTHALPIES") {
            ReportLine("h_steam(P,T_in)", "${fmt(params.hSteam)} kJ/kg")
            ReportLine("h_spray(P,T_spray)", "${fmt(params.hSpray)} kJ/kg")
            if (params.mode == "B") {
                ReportLine("h_out(mix)", "${fmt(params.hOut)} kJ/kg")
            } else {
                ReportLine("h_target(P,T_out)", "${fmt(params.hOut)} kJ/kg")
            }
        }

        // ── Calculation Result ───────────────────────────────────────
        ReportSection("CALCULATION RESULT") {
            if (params.mode == "B") {
                ReportLine("Outlet temperature", "${fmt(params.outletTemp)} °C")
                ReportLine("Temperature drop", "${fmt(params.steamTemp - params.outletTemp)} °C")
            } else if (params.mode == "A") {
                ReportLine("Required spray flow", "%.4f".format(params.sprayFlow) + " t/h")
                ReportLine("Temperature drop", "${fmt(params.steamTemp - params.targetTemp)} °C")
            } else {
                ReportLine("Metal temp (final)", "${fmt(params.metalTemp)} °C")
                ReportLine("Net heat", "${fmt(params.netHeat)} MW")
            }
        }

        Spacer(Modifier.height(16.dp))

        OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
            Text("← Back to Calculator")
        }
        Spacer(Modifier.height(32.dp))
    }
}

@Composable
private fun ReportSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.onSurface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(bottom = 8.dp))
            content()
        }
    }
}

@Composable
private fun ReportLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth().padding(bottom = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
        Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium,
            fontFamily = FontFamily.Monospace)
    }
}

private fun fmt(v: Double): String = "%.1f".format(v)

private data class EBParams(
    val mode: String, val steamFlow: Double, val steamPressure: Double,
    val steamTemp: Double, val targetTemp: Double, val sprayTemp: Double,
    val sprayFlow: Double, val hSteam: Double, val hSpray: Double,
    val hOut: Double, val initialMetalTemp: Double, val metalTemp: Double,
    val netHeat: Double, val outletTemp: Double
)

private fun parseEnergyBalanceData(data: String): EBParams {
    val decoded = try { URLDecoder.decode(data, "UTF-8") } catch (_: Exception) { data }
    val map = decoded.split(";").associate {
        val parts = it.split("=", limit = 2)
        if (parts.size == 2) parts[0].trim() to parts[1].trim() else "" to ""
    }
    return EBParams(
        mode = map["mode"] ?: "A",
        steamFlow = map["steamFlow"]?.toDoubleOrNull() ?: 0.0,
        steamPressure = map["steamPressure"]?.toDoubleOrNull() ?: 0.0,
        steamTemp = map["steamTemp"]?.toDoubleOrNull() ?: 0.0,
        targetTemp = map["targetTemp"]?.toDoubleOrNull() ?: 0.0,
        sprayTemp = map["sprayTemp"]?.toDoubleOrNull() ?: 0.0,
        sprayFlow = map["sprayFlow"]?.toDoubleOrNull() ?: 0.0,
        hSteam = map["hSteam"]?.toDoubleOrNull() ?: 0.0,
        hSpray = map["hSpray"]?.toDoubleOrNull() ?: 0.0,
        hOut = map["hOut"]?.toDoubleOrNull() ?: 0.0,
        initialMetalTemp = map["initialMetalTemp"]?.toDoubleOrNull() ?: 0.0,
        metalTemp = map["metalTemp"]?.toDoubleOrNull() ?: 0.0,
        netHeat = map["netHeat"]?.toDoubleOrNull() ?: 0.0,
        outletTemp = map["outletTemp"]?.toDoubleOrNull() ?: 0.0
    )
}
