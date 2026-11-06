package com.steamcalc.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import com.steamcalc.util.Units

@Composable
fun HistoryScreen(
    onOpenResults: (String) -> Unit,
    viewModel: HistoryViewModel = hiltViewModel(),
) {
    val runs by viewModel.runs.collectAsStateWithLifecycle()

    if (runs.isEmpty()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("No saved runs yet.", style = MaterialTheme.typography.titleMedium)
            Text(
                "Steady, transient and burner runs are stored on the device.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(runs, key = { it.id }) { run ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpenResults(run.id) },
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(run.label, style = MaterialTheme.typography.titleMedium)
                        Text(
                            SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date(run.createdAt)),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            "Outlet ${Units.withUnit(run.tOutC, Units.TEMPERATURE)} · " +
                                "Metal ${Units.withUnit(run.tMetalC, Units.TEMPERATURE)} · " +
                                "Q ${Units.withUnit(run.qPlatenMW, Units.POWER)}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                    IconButton(onClick = { viewModel.delete(run.id) }) {
                        Icon(Icons.Default.DeleteOutline, contentDescription = "Delete")
                    }
                }
            }
        }
    }
}
