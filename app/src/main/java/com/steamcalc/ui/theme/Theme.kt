package com.steamcalc.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.steamcalc.R

private val Blue = Color(0xFF0B5FFF)
private val BlueDark = Color(0xFF8FB4FF)
private val Teal = Color(0xFF00796B)
private val TealDark = Color(0xFF7FD8CC)
private val Alert = Color(0xFFB3261E)
private val AlertDark = Color(0xFFFFB4AB)

private val LightColors = lightColorScheme(
    primary = Blue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCE6FF),
    onPrimaryContainer = Color(0xFF001945),
    secondary = Teal,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFB8F1E8),
    onSecondaryContainer = Color(0xFF00201C),
    background = Color(0xFFF7F9FC),
    onBackground = Color(0xFF101418),
    surface = Color.White,
    onSurface = Color(0xFF101418),
    surfaceVariant = Color(0xFFE6EAF1),
    onSurfaceVariant = Color(0xFF44474E),
    error = Alert,
)

private val DarkColors = darkColorScheme(
    primary = BlueDark,
    onPrimary = Color(0xFF002B75),
    primaryContainer = Color(0xFF003C9B),
    onPrimaryContainer = Color(0xFFDCE6FF),
    secondary = TealDark,
    onSecondary = Color(0xFF00372F),
    secondaryContainer = Color(0xFF005045),
    onSecondaryContainer = Color(0xFFB8F1E8),
    background = Color(0xFF0F1319),
    onBackground = Color(0xFFE2E4E9),
    surface = Color(0xFF161B22),
    onSurface = Color(0xFFE2E4E9),
    surfaceVariant = Color(0xFF2A3038),
    onSurfaceVariant = Color(0xFFC4C7CE),
    error = AlertDark,
)

/** Vazirmatn is bundled so the Persian About screen renders consistently. */
val Vazirmatn = FontFamily(
    Font(R.font.vazirmatn, FontWeight.Normal),
)

private val AppTypography = Typography(
    titleLarge = TextStyle(fontSize = 22.sp, lineHeight = 28.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 17.sp, lineHeight = 24.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 15.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp),
    labelLarge = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Medium),
)

@Composable
fun PlatenTwinTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}
