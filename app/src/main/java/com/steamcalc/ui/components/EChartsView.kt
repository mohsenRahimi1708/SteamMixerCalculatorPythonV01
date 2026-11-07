package com.steamcalc.ui.components

import android.annotation.SuppressLint
import android.graphics.Color
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import org.json.JSONObject

/**
 * WebView-hosted Apache ECharts surface.
 *
 * Interactive by construction: zoom (pinch / dataZoom), pan, legend toggling,
 * tooltips and multi-series combination all come from the ECharts option the
 * caller supplies.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun EChartsView(
    optionJson: String,
    modifier: Modifier = Modifier,
    captureToken: Int = 0,
    onCaptured: (String) -> Unit = {},
) {
    var webView by remember { mutableStateOf<WebView?>(null) }
    var ready by remember { mutableStateOf(false) }
    var pending by remember { mutableStateOf(optionJson) }

    AndroidView(
        modifier = modifier,
        factory = { context ->
            WebView(context).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.allowFileAccess = true
                settings.loadWithOverviewMode = true
                settings.useWideViewPort = true
                setBackgroundColor(Color.WHITE)
                webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView?, url: String?) {
                        super.onPageFinished(view, url)
                        ready = true
                        view?.evaluateJavascript("setOption(" + JSONObject.quote(pending) + ")", null)
                    }
                }
                loadUrl("file:///android_asset/echarts.html")
                webView = this
            }
        },
        update = { view ->
            if (ready) {
                view.evaluateJavascript("setOption(" + JSONObject.quote(pending) + ")", null)
            }
        },
    )

    LaunchedEffect(optionJson) {
        pending = optionJson
        if (ready) {
            webView?.evaluateJavascript("setOption(" + JSONObject.quote(optionJson) + ")", null)
        }
    }

    LaunchedEffect(captureToken) {
        if (captureToken > 0 && ready) {
            webView?.evaluateJavascript("capturePng()") { result ->
                val cleaned = result
                    .removePrefix("\"")
                    .removeSuffix("\"")
                    .replace("\\/", "/")
                if (cleaned.startsWith("data:image")) onCaptured(cleaned)
            }
        }
    }

    Box(modifier = modifier)
}
