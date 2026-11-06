package com.steamcalc.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType

/**
 * Labelled numeric field that always shows its unit.
 *
 * The unit is part of the layout, so a number can never be read without knowing
 * whether it is t/h, °C, bar or MW.
 */
@Composable
fun NumberField(
    label: String,
    value: String,
    unit: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val invalid = value.isNotBlank() && value.toDoubleOrNull() == null
    OutlinedTextField(
        modifier = modifier.fillMaxWidth(),
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        trailingIcon = { Text(unit, style = androidx.compose.material3.MaterialTheme.typography.labelLarge) },
        isError = invalid,
        singleLine = true,
        enabled = enabled,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
    )
}
