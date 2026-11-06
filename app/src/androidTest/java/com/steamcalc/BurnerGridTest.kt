package com.steamcalc

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.steamcalc.domain.BurnerLayout
import com.steamcalc.ui.components.BurnerGrid
import com.steamcalc.ui.theme.PlatenTwinTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

/** Compose UI test: the grid renders 24 burners and reports taps. */
class BurnerGridTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun burnerGridRendersAllTagsAndReportsTaps() {
        var tapped: String? = null
        composeRule.setContent {
            PlatenTwinTheme {
                BurnerGrid(
                    states = emptyMap(),
                    onToggle = { tapped = it.tag },
                    onEdit = {},
                )
            }
        }
        composeRule.onNodeWithText("FA1").assertIsDisplayed()
        composeRule.onNodeWithText("FA1").performClick()
        assertEquals("FA1", tapped)
        assertEquals(24, BurnerLayout.burners.size)
    }
}
