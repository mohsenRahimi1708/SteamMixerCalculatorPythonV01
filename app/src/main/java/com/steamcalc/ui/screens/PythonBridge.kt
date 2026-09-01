package com.steamcalc.ui.screens

import android.util.Log
import com.chaquo.python.Python

private const val TAG = "PythonBridge"

/**
 * Call a Python engine function and return the result as a flat Map<String, Any?>.
 */
fun callEngine(moduleName: String, funcName: String, vararg args: Any?): Map<String, Any?> {
    Log.d(TAG, "callEngine: $moduleName.$funcName(${args.joinToString { it.toString().take(30) }})")
    val py = Python.getInstance()
    val module = py.getModule(moduleName)
    Log.d(TAG, "Got module: $moduleName")
    val pyResult = module.callAttr(funcName, *args)
    Log.d(TAG, "callAttr returned: ${pyResult.javaClass.simpleName}")
    @Suppress("UNCHECKED_CAST")
    val raw = pyResult.asMap() as Map<Any, Any>
    Log.d(TAG, "raw map keys: ${raw.keys}")
    val result = raw.mapKeys { it.key.toString() }.mapValues { convertPyValue(it.value) }
    Log.d(TAG, "Final result keys: ${result.keys}, status=${result["status"]}")
    return result
}

fun convertPyValue(value: Any?): Any? {
    return when (value) {
        is Map<*, *> -> value.mapKeys { it.key.toString() }.mapValues { convertPyValue(it.value) }
        is List<*> -> value.map { convertPyValue(it) }
        else -> value
    }
}
