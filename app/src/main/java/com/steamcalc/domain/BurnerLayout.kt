package com.steamcalc.domain

/**
 * Static burner layout, mirroring the plant documentation.
 *
 * Kept locally so the burner grid renders even before the first frame from the
 * server arrives; the server remains the authority on the layout.
 */
object BurnerLayout {
    const val BOILER_WIDTH_M = 20.0
    const val RATED_MW = 40.0
    val levels = listOf("A", "B", "C")
    val levelElevationM = mapOf("A" to 9.0, "B" to 12.0, "C" to 15.0)

    val burners: List<BurnerSpec> = buildList {
        for (level in levels) {
            for ((row, prefix) in listOf("front" to "F", "rear" to "R")) {
                for (index in 1..4) {
                    add(
                        BurnerSpec(
                            tag = "$prefix$level$index",
                            level = level,
                            row = row,
                            index = index,
                            elevationM = levelElevationM.getValue(level),
                            lateralM = (index - 0.5) * BOILER_WIDTH_M / 4.0,
                            ratedMW = RATED_MW,
                        ),
                    )
                }
            }
        }
    }

    fun byTag(tag: String): BurnerSpec? = burners.firstOrNull { it.tag == tag }
}
