package com.steamcalc.util

import java.util.Locale

/**
 * The only units the app may ever display or transmit.
 *
 * Mass flow t/h, temperature °C, pressure bar, heat rate MW, heat transfer
 * coefficient W/m²K. Conversions to SI exist only inside the Python solver.
 */
object Units {
    const val FLOW = "t/h"
    const val TEMPERATURE = "°C"
    const val PRESSURE = "bar"
    const val POWER = "MW"
    const val HTC = "W/m²K"
    const val SECONDS = "s"

    /** Format a number with a fixed number of decimals and no thousands separator. */
    fun fmt(value: Double?, decimals: Int = 1): String {
        if (value == null || value.isNaN() || value.isInfinite()) return "—"
        return String.format(Locale.US, "%.${decimals}f", value)
    }

    /** Format a number followed by its unit. */
    fun withUnit(value: Double?, unit: String, decimals: Int = 1): String =
        "${fmt(value, decimals)} $unit"

    /** Format a large count (Reynolds number) with no decimals. */
    fun count(value: Double?): String {
        if (value == null || value.isNaN() || value.isInfinite()) return "—"
        return String.format(Locale.US, "%.0f", value)
    }
}
