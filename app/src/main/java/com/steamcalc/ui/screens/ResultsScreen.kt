package com.steamcalc.ui.screens

import android.content.Context
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.steamcalc.ui.components.EChartsView
import com.steamcalc.ui.components.ErrorBanner
import com.steamcalc.ui.components.SectionCard
import com.steamcalc.ui.components.WarningList
import com.steamcalc.util.ExportUtil

@Composable
fun ResultsScreen(viewModel: ResultsViewModel = hiltViewModel()) {
    val run by viewModel.run.collectAsStateWithLifecycle()
    val series by viewModel.series.collectAsStateWithLifecycle()
    val selected by viewModel.selected.collectAsStateWithLifecycle()
    val summary by viewModel.summary.collectAsStateWithLifecycle()
    val error by viewModel.error.collectAsStateWithLifecycle()
    val captureToken by viewModel.captureToken.collectAsStateWithLifecycle()
    val context = LocalContext.current

    val option = remember(series, selected) { viewModel.chartOption() }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            run?.label ?: "Results",
            style = MaterialTheme.typography.titleLarge,
        )
        Text(
            run?.let { "Saved ${java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.US).format(java.util.Date(it.createdAt))}" }
                ?: "Loading…",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        error?.let { ErrorBanner(it) }

        if (series.isNotEmpty()) {
            SectionCard(title = "Chart", subtitle = "Pinch to zoom · tap the legend to combine series") {
                EChartsView(
                    optionJson = option,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(320.dp),
                    captureToken = captureToken,
                    onCaptured = { dataUrl ->
                        ExportUtil.png(context, "platen-chart.png", dataUrl)?.let { uri ->
                            ExportUtil.share(context, uri, "image/png")
                        }
                    },
                )
            }
            SectionCard(title = "Series", subtitle = "Select the quantities to overlay") {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    series.take(4).forEach { item ->
                        FilterChip(
                            selected = selected.contains(item.key),
                            onClick = { viewModel.toggle(item.key) },
                            label = { Text(item.label) },
                        )
                    }
                }
                if (series.size > 4) {
                    Spacer(Modifier.height(6.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        series.drop(4).forEach { item ->
                            FilterChip(
                                selected = selected.contains(item.key),
                                onClick = { viewModel.toggle(item.key) },
                                label = { Text(item.label) },
                            )
                        }
                    }
                }
            }
        }

        if (summary.isNotEmpty()) {
            SectionCard(title = "Values") {
                summary.forEach { (label, value) ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 3.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(label, style = MaterialTheme.typography.bodyMedium)
                        Text(
                            value,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }
        }

        if (!run?.warnings.isNullOrEmpty()) {
            SectionCard(title = "Warnings") {
                WarningList(run?.warnings ?: emptyList())
            }
        }

        HorizontalDivider()
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = {
                viewModel.csvPayload()?.let { payload ->
                    ExportUtil.csv(context, payload.fileName, payload.header, payload.rows)?.let { uri ->
                        ExportUtil.share(context, uri, "text/csv")
                    }
                }
            }) { Text("Export CSV") }
            Button(
                onClick = { viewModel.requestPng() },
                enabled = series.isNotEmpty(),
            ) { Text("Export PNG") }
        }
        Text(
            "All values in t/h, °C, bar, MW and W/m²K.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private fun formatTime(context: Context, millis: Long): String =
    java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.getDefault())
        .format(java.util.Date(millis))
