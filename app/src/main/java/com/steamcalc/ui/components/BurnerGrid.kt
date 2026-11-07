package com.steamcalc.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.steamcalc.domain.BurnerLayout
import com.steamcalc.domain.BurnerSpec
import com.steamcalc.util.Units

/**
 * Interactive burner grid: three levels, front and rear rows, four burners each.
 *
 * Tap toggles ignition state, long press opens the per-burner load / ramp editor.
 */
@Composable
fun BurnerGrid(
    states: Map<String, Double>,
    onToggle: (BurnerSpec) -> Unit,
    onEdit: (BurnerSpec) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        for (level in BurnerLayout.levels) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
                    .padding(10.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "Level $level",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        Units.withUnit(BurnerLayout.levelElevationM[level], "m", 0),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Spacer(Modifier.size(6.dp))
                BurnerRow(level = level, row = "front", states = states, onToggle = onToggle, onEdit = onEdit)
                Spacer(Modifier.size(4.dp))
                BurnerRow(level = level, row = "rear", states = states, onToggle = onToggle, onEdit = onEdit)
            }
        }
    }
}

@Composable
private fun BurnerRow(
    level: String,
    row: String,
    states: Map<String, Double>,
    onToggle: (BurnerSpec) -> Unit,
    onEdit: (BurnerSpec) -> Unit,
) {
    val burners = BurnerLayout.burners.filter { it.level == level && it.row == row }
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(
            if (row == "front") "F" else "R",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.width(12.dp),
        )
        burners.forEach { burner ->
            BurnerIcon(
                burner = burner,
                load = states[burner.tag] ?: 0.0,
                onToggle = { onToggle(burner) },
                onEdit = { onEdit(burner) },
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun BurnerIcon(
    burner: BurnerSpec,
    load: Double,
    onToggle: () -> Unit,
    onEdit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val on = load > 0.01
    val glow by animateFloatAsState(targetValue = (0.25f + 0.75f * load.toFloat()).coerceIn(0f, 1f), label = "glow")
    val background by animateColorAsState(
        targetValue = if (on) MaterialTheme.colorScheme.primary.copy(alpha = 0.15f + 0.35f * glow)
        else MaterialTheme.colorScheme.surfaceVariant,
        label = "burnerBackground",
    )
    val flame = if (on) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant

    Column(
        modifier = modifier
            .combinedClickable(onClick = onToggle, onLongClick = onEdit)
            .background(background, RoundedCornerShape(10.dp))
            .padding(vertical = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(26.dp),
            contentAlignment = Alignment.Center,
        ) {
            Box(
                modifier = Modifier
                    .size(24.dp)
                    .alpha(if (on) 0.9f else 0.45f)
                    .background(
                        if (on) flame else Color(0xFF9AA0A6),
                        CircleShape,
                    ),
            )
            Text(
                text = if (on) "🔥" else "",
                fontSize = 11.sp,
            )
        }
        Text(
            burner.tag,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = if (on) FontWeight.SemiBold else FontWeight.Normal,
            color = flame,
        )
        Text(
            "${(load * 100).toInt()}%",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
