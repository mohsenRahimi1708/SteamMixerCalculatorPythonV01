package com.steamcalc.util

import java.util.Locale

/**
 * Minimal ECharts option builder.
 *
 * Produces an option object with zoom, pan, legend toggling and tooltips; series
 * can target either of the two value axes so temperature and heat rate can be
 * compared without distorting the y scales.
 */
object EchartsOptions {

    data class Series(
        val name: String,
        val unit: String,
        val x: List<Double>,
        val y: List<Double>,
        val axisIndex: Int = 0,
    )

    /** Downsample to at most [maxPoints] points, keeping the first and last. */
    fun decimate(series: Series, maxPoints: Int = 600): Series {
        if (series.x.size <= maxPoints || maxPoints < 3) return series
        val stride = (series.x.size - 1) / (maxPoints - 1).toDouble()
        val x = ArrayList<Double>(maxPoints)
        val y = ArrayList<Double>(maxPoints)
        var index = 0
        while (index < series.x.size) {
            x.add(series.x[index])
            y.add(series.y[index])
            index = (index + stride.toInt().coerceAtLeast(1))
        }
        if (x.last() != series.x.last()) {
            x.add(series.x.last())
            y.add(series.y.last())
        }
        return series.copy(x = x, y = y)
    }

    fun line(
        title: String,
        xName: String,
        series: List<Series>,
        leftName: String,
        rightName: String,
    ): String {
        val prepared = series.map { decimate(it) }
        val hasRight = prepared.any { it.axisIndex == 1 }
        val builder = StringBuilder(4096)
        builder.append("{\"backgroundColor\":\"#ffffff\",\"animation\":false,")
        builder.append("\"textStyle\":{\"fontFamily\":\"sans-serif\"},")
        builder.append("\"title\":{\"text\":").append(quote(title))
            .append(",\"left\":\"center\",\"top\":4,\"textStyle\":{\"fontSize\":12,\"fontWeight\":\"normal\"}},")
        builder.append("\"tooltip\":{\"trigger\":\"axis\"},")
        builder.append("\"legend\":{\"top\":26,\"type\":\"scroll\",\"itemWidth\":12,\"itemHeight\":8,\"textStyle\":{\"fontSize\":10}},")
        builder.append("\"grid\":{\"left\":54,\"right\":")
            .append(if (hasRight) 56 else 16)
            .append(",\"top\":64,\"bottom\":46,\"containLabel\":false},")
        builder.append("\"dataZoom\":[{\"type\":\"inside\"},{\"type\":\"slider\",\"height\":16,\"bottom\":6}],")
        builder.append("\"xAxis\":{\"type\":\"value\",\"name\":").append(quote(xName))
            .append(",\"nameLocation\":\"middle\",\"nameGap\":24,\"axisLabel\":{\"fontSize\":9},\"axisPointer\":{\"label\":{\"show\":false}}},")
        builder.append("\"yAxis\":[{\"type\":\"value\",\"scale\":true,\"name\":").append(quote(leftName))
            .append(",\"nameTextStyle\":{\"fontSize\":9},\"axisLabel\":{\"fontSize\":9},\"splitLine\":{\"lineStyle\":{\"type\":\"dashed\"}}}")
        if (hasRight) {
            builder.append(",{\"type\":\"value\",\"scale\":true,\"name\":").append(quote(rightName))
                .append(",\"nameTextStyle\":{\"fontSize\":9},\"axisLabel\":{\"fontSize\":9},\"splitLine\":{\"show\":false}}")
        }
        builder.append("],\"series\":[")
        prepared.forEachIndexed { index, item ->
            if (index > 0) builder.append(',')
            val unit = if (item.unit.isBlank()) "" else item.unit
            builder.append("{\"name\":").append(quote(item.name))
                .append(",\"type\":\"line\",\"showSymbol\":false,\"sampling\":\"lttb\"")
                .append(",\"yAxisIndex\":").append(item.axisIndex)
                .append(",\"lineStyle\":{\"width\":1.6}")
                .append(",\"emphasis\":{\"focus\":\"series\"}")
                .append(",\"data\":[")
            for (point in item.x.indices) {
                if (point > 0) builder.append(',')
                builder.append('[').append(number(item.x[point])).append(',')
                    .append(number(item.y[point])).append(']')
            }
            builder.append("],\"tooltip\":{\"valueFormatter\":\"").append(unit).append("\"}}")
        }
        builder.append("]}")
        return builder.toString()
    }

    /** Simple single-series bar chart, used for steady-state comparison. */
    fun bars(title: String, categories: List<String>, values: List<Double>, unit: String): String {
        val builder = StringBuilder(1024)
        builder.append("{\"backgroundColor\":\"#ffffff\",\"animation\":false,")
        builder.append("\"title\":{\"text\":").append(quote(title)).append(",\"left\":\"center\",\"textStyle\":{\"fontSize\":12}},")
        builder.append("\"tooltip\":{\"trigger\":\"axis\",\"valueFormatter\":\"").append(unit).append("\"},")
        builder.append("\"grid\":{\"left\":52,\"right\":16,\"top\":40,\"bottom\":36},")
        builder.append("\"xAxis\":{\"type\":\"category\",\"data\":[")
        categories.forEachIndexed { index, category ->
            if (index > 0) builder.append(',')
            builder.append(quote(category))
        }
        builder.append("],\"axisLabel\":{\"fontSize\":9}},")
        builder.append("\"yAxis\":{\"type\":\"value\",\"scale\":true,\"axisLabel\":{\"fontSize\":9}},")
        builder.append("\"series\":[{\"type\":\"bar\",\"data\":[")
        values.forEachIndexed { index, value ->
            if (index > 0) builder.append(',')
            builder.append(number(value))
        }
        builder.append("],\"itemStyle\":{\"color\":\"#0B5FFF\"}}]}")
        return builder.toString()
    }

    private fun quote(value: String): String {
        val escaped = value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", " ")
        return "\"$escaped\""
    }

    private fun number(value: Double): String =
        if (value.isNaN() || value.isInfinite()) "null"
        else String.format(Locale.US, "%.4f", value)
}
