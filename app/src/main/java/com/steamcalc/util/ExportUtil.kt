package com.steamcalc.util

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Base64
import androidx.core.content.FileProvider
import java.io.File

/** CSV and PNG export through the app FileProvider. */
object ExportUtil {

    private const val AUTHORITY_SUFFIX = ".fileprovider"

    fun csv(
        context: Context,
        fileName: String,
        header: List<String>,
        rows: List<List<String>>,
    ): Uri? = runCatching {
        val directory = File(context.cacheDir, "exports").apply { mkdirs() }
        val file = File(directory, fileName)
        file.writeText(buildString {
            appendLine(header.joinToString(","))
            rows.forEach { row ->
                appendLine(row.joinToString(",") { cell ->
                    if (cell.contains(',') || cell.contains('"')) {
                        "\"" + cell.replace("\"", "\"\"") + "\""
                    } else {
                        cell
                    }
                })
            }
        })
        FileProvider.getUriForFile(context, context.packageName + AUTHORITY_SUFFIX, file)
    }.getOrNull()

    fun png(context: Context, fileName: String, dataUrl: String): Uri? = runCatching {
        val base64 = dataUrl.substringAfter("base64,", dataUrl)
        val bytes = Base64.decode(base64, Base64.DEFAULT)
        val directory = File(context.cacheDir, "exports").apply { mkdirs() }
        val file = File(directory, fileName)
        file.writeBytes(bytes)
        FileProvider.getUriForFile(context, context.packageName + AUTHORITY_SUFFIX, file)
    }.getOrNull()

    fun share(context: Context, uri: Uri, mimeType: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "Export"))
    }
}
