package com.steamcalc.ui.screens

import com.chaquo.python.Python

/**
 * Call a Python engine function and return the result as a flat Map<String, Any?>.
 * Chaquopy returns Map<PyObject, PyObject> which we flatten to string keys.
 * Nested Python dicts are recursively converted to Map<String, Any?>.
 */
fun callEngine(moduleName: String, funcName: String, vararg args: Any?): Map<String, Any?> {
    val py = Python.getInstance()
    val module = py.getModule(moduleName)
    val pyResult = module.callAttr(funcName, *args)
    @Suppress("UNCHECKED_CAST")
    val raw = pyResult.asMap() as Map<Any, Any>
    return raw.mapKeys { it.key.toString() }.mapValues { convertPyValue(it.value) }
}

/**
 * Recursively convert a PyObject value to a Kotlin-friendly type.
 * Nested maps become Map<String, Any?>, lists stay as-is.
 */
fun convertPyValue(value: Any?): Any? {
    return when (value) {
        is Map<*, *> -> value.mapKeys { it.key.toString() }.mapValues { convertPyValue(it.value) }
        is List<*> -> value.map { convertPyValue(it) }
        else -> value
    }
}
