package com.steamcalc.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.steamcalc.R
import com.steamcalc.ui.theme.Vazirmatn

/**
 * About screen, fully Persian and right-to-left by construction.
 *
 * The layout direction is forced rather than inherited so the screen renders
 * correctly even on a device configured with an English locale.
 */
@Composable
fun AboutScreen() {
    val sections = listOf(
        R.string.about_purpose to R.string.about_purpose_text,
        R.string.about_platen to R.string.about_platen_text,
        R.string.about_modes to R.string.about_modes_text,
        R.string.about_units to R.string.about_units_text,
        R.string.about_formula to R.string.about_formula_text,
        R.string.about_htc to R.string.about_htc_text,
        R.string.about_regimes to R.string.about_regimes_text,
        R.string.about_initial to R.string.about_initial_text,
        R.string.about_burner to R.string.about_burner_text,
        R.string.about_disclaimer to R.string.about_disclaimer_text,
        R.string.about_version to R.string.about_version_text,
        R.string.about_contact to R.string.about_contact_text,
    )

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 12.dp),
        ) {
            Text(
                text = stringResource(R.string.about_title),
                style = MaterialTheme.typography.titleLarge,
                fontFamily = Vazirmatn,
                textAlign = TextAlign.Right,
                fontSize = 22.sp,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "دوقلوی دیجیتال پلیتن سوپرهیتر — نسخهٔ ۴٫۰٫۰",
                style = MaterialTheme.typography.bodyMedium,
                fontFamily = Vazirmatn,
                textAlign = TextAlign.Right,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            HorizontalDivider()

            sections.forEach { (titleRes, bodyRes) ->
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(titleRes),
                    style = MaterialTheme.typography.titleMedium,
                    fontFamily = Vazirmatn,
                    textAlign = TextAlign.Right,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = stringResource(bodyRes),
                    style = MaterialTheme.typography.bodyLarge,
                    fontFamily = Vazirmatn,
                    textAlign = TextAlign.Right,
                    lineHeight = 26.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            Spacer(Modifier.height(24.dp))
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                Text(
                    "نسخهٔ برنامه: ۴٫۰٫۰ (versionCode 4)",
                    fontFamily = Vazirmatn,
                    textAlign = TextAlign.Right,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    "هستهٔ محاسباتی: Python 3.11 · FastAPI · IAPWS-IF97",
                    fontFamily = Vazirmatn,
                    textAlign = TextAlign.Right,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}
