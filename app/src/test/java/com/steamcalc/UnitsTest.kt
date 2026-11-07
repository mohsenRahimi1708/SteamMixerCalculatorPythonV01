package com.steamcalc

import com.steamcalc.util.EchartsOptions
import com.steamcalc.util.Units
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Unit tests for the display-unit contract and the chart option builder. */
class UnitsTest {

    @Test
    fun `units are the four contractual ones`() {
        assertEquals("t/h", Units.FLOW)
        assertEquals("°C", Units.TEMPERATURE)
        assertEquals("bar", Units.PRESSURE)
        assertEquals("MW", Units.POWER)
        assertEquals("W/m²K", Units.HTC)
    }

    @Test
    fun `formatting rounds to the requested decimals`() {
        assertEquals("540.0", Units.fmt(540.0, 1))
        assertEquals("540.00", Units.fmt(540.0, 2))
        assertEquals("1234.6", Units.fmt(1234.567, 1))
    }

    @Test
    fun `invalid numbers render as a dash`() {
        assertEquals("—", Units.fmt(Double.NaN, 1))
        assertEquals("—", Units.fmt(null, 1))
        assertEquals("—", Units.fmt(Double.POSITIVE_INFINITY, 1))
    }

    @Test
    fun `value with unit keeps them together`() {
        assertEquals("167.0 bar", Units.withUnit(167.0, Units.PRESSURE))
    }

    @Test
    fun `chart option is valid JSON with zoom legend and axis names`() {
        val option = EchartsOptions.line(
            title = "Transient",
            xName = "s",
            series = listOf(
                EchartsOptions.Series("Outlet", "°C", listOf(0.0, 2.0), listOf(540.0, 541.0)),
                EchartsOptions.Series("Heat", "MW", listOf(0.0, 2.0), listOf(24.0, 24.5), axisIndex = 1),
            ),
            leftName = "°C",
            rightName = "MW",
        )
        assertTrue(option.contains("\"dataZoom\""))
        assertTrue(option.contains("\"legend\""))
        assertTrue(option.contains("\"title\""))
        assertTrue(option.contains("\"name\":\"°C\""))
        assertTrue(option.contains("\"yAxisIndex\":1"))
        assertTrue(option.startsWith("{"))
        assertTrue(option.endsWith("}"))
    }

    @Test
    fun `decimation keeps the series bounded and the last point`() {
        val x = (0 until 2000).map { it.toDouble() }
        val y = x.map { it * 2 }
        val reduced = EchartsOptions.decimate(EchartsOptions.Series("t", "°C", x, y), maxPoints = 100)
        assertTrue(reduced.x.size <= 101)
        assertEquals(x.last(), reduced.x.last(), 0.0)
    }
}
