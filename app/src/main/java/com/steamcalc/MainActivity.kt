package com.steamcalc

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.steamcalc.ui.nav.AppRoot
import com.steamcalc.ui.theme.PlatenTwinTheme
import dagger.hilt.android.AndroidEntryPoint

/** Single-activity host for the Compose UI. */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PlatenTwinTheme {
                AppRoot()
            }
        }
    }
}
