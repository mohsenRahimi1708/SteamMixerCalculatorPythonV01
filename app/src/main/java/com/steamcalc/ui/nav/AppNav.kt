package com.steamcalc.ui.nav

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Calculate
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.steamcalc.ui.screens.AboutScreen
import com.steamcalc.ui.screens.BurnerStartupScreen
import com.steamcalc.ui.screens.HistoryScreen
import com.steamcalc.ui.screens.HomeScreen
import com.steamcalc.ui.screens.ResultsScreen
import com.steamcalc.ui.screens.SettingsScreen
import com.steamcalc.ui.screens.SteadyStateScreen
import com.steamcalc.ui.screens.TransientScreen

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab("home", "Home", Icons.Default.Home),
    Tab("steady", "Steady", Icons.Default.Calculate),
    Tab("transient", "Transient", Icons.Default.Timeline),
    Tab("burner", "Burners", Icons.Default.LocalFireDepartment),
    Tab("history", "History", Icons.Default.History),
)

private val titles = mapOf(
    "home" to "Platen superheater",
    "steady" to "Steady state",
    "transient" to "Transient",
    "burner" to "Burners",
    "history" to "History",
    "about" to "About",
    "settings" to "Settings",
    "results" to "Results",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppRoot() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val destination = backStackEntry?.destination
    val currentRoute = destination?.route
    val showBottomBar = tabs.any { tab ->
        destination?.hierarchy?.any { it.route == tab.route } == true
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        titles[currentRoute?.substringBefore("/") ?: "home"] ?: "Platen superheater",
                        fontWeight = FontWeight.SemiBold,
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                ),
                actions = {
                    IconButton(onClick = { navController.navigate("about") }) {
                        Icon(Icons.Default.Info, contentDescription = "About")
                    }
                    IconButton(onClick = { navController.navigate("settings") }) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    tabs.forEach { tab ->
                        val selected = destination?.hierarchy?.any { it.route == tab.route } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(tab.route) {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = Modifier.padding(padding),
        ) {
            composable("home") {
                HomeScreen(onNavigate = { route -> navController.navigate(route) })
            }
            composable("steady") { SteadyStateScreen() }
            composable("transient") {
                TransientScreen(onOpenResults = { id -> navController.navigate("results/$id") })
            }
            composable("burner") {
                BurnerStartupScreen(onOpenResults = { id -> navController.navigate("results/$id") })
            }
            composable("history") {
                HistoryScreen(onOpenResults = { id -> navController.navigate("results/$id") })
            }
            composable("about") { AboutScreen() }
            composable("settings") { SettingsScreen() }
            composable(
                route = "results/{runId}",
                arguments = listOf(navArgument("runId") { type = NavType.StringType }),
            ) {
                ResultsScreen()
            }
        }
    }
}
