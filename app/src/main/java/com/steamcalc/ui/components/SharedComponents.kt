package com.steamcalc.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp

/**
 * Shared initial metal temperature input field — used on every screen.
 */
@Composable
fun MetalTempInput(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    SectionHeader("Initial Platen Metal Temperature", Color(0xFFFF6F00))
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text("Initial metal temperature (°C) *") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        modifier = modifier.fillMaxWidth().padding(bottom = 16.dp),
        singleLine = true,
        supportingText = { Text("Required — starting condition for all calculations") }
    )
}

@Composable
fun SectionHeader(title: String, color: Color) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.Bold,
        color = color,
        modifier = Modifier.padding(bottom = 8.dp)
    )
}
