package com.steamcalc.domain

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

// ---------------------------------------------------------------------------
// Requests (field names mirror the REST contract exactly)
// ---------------------------------------------------------------------------

@Serializable
data class SteadyRequest(
    @SerialName("m_main_tph") val mMainTph: Double,
    @SerialName("T_main_C") val tMainC: Double,
    @SerialName("P_main_bar") val pMainBar: Double,
    @SerialName("m_spray_tph") val mSprayTph: Double,
    @SerialName("T_LT_out_C") val tLtOutC: Double,
    @SerialName("Q_platen_MW") val qPlatenMW: Double,
    @SerialName("htc_method") val htcMethod: String,
)

@Serializable
data class TransientRequest(
    @SerialName("m_main_tph") val mMainTph: Double,
    @SerialName("T_main_C") val tMainC: Double,
    @SerialName("P_main_bar") val pMainBar: Double,
    @SerialName("m_spray_tph") val mSprayTph: Double,
    @SerialName("T_LT_out_C") val tLtOutC: Double,
    @SerialName("Q_platen_MW") val qPlatenMW: Double,
    @SerialName("htc_method") val htcMethod: String,
    @SerialName("duration_s") val durationS: Double,
    @SerialName("dt_s") val dtS: Double,
    @SerialName("initial_mode") val initialMode: String,
    @SerialName("T_metal_init_C") val tMetalInitC: Double? = null,
    @SerialName("Q_platen_init_MW") val qPlatenInitMW: Double? = null,
    @SerialName("previous_run_id") val previousRunId: String? = null,
    val heating: Boolean = true,
    @SerialName("n_nodes") val nNodes: Int = 1,
)

@Serializable
data class BurnerEventInput(
    val tag: String,
    @SerialName("time_s") val timeS: Double = 0.0,
    val state: String = "on",
    @SerialName("target_load_fraction") val targetLoadFraction: Double = 1.0,
    @SerialName("ramp_time_s") val rampTimeS: Double = 30.0,
)

@Serializable
data class BurnerStartupRequest(
    @SerialName("m_main_tph") val mMainTph: Double,
    @SerialName("T_main_C") val tMainC: Double,
    @SerialName("P_main_bar") val pMainBar: Double,
    @SerialName("m_spray_tph") val mSprayTph: Double,
    @SerialName("T_LT_out_C") val tLtOutC: Double,
    @SerialName("Q_platen_MW") val qPlatenMW: Double,
    @SerialName("htc_method") val htcMethod: String,
    @SerialName("duration_s") val durationS: Double,
    @SerialName("dt_s") val dtS: Double,
    @SerialName("initial_mode") val initialMode: String,
    @SerialName("T_metal_init_C") val tMetalInitC: Double? = null,
    @SerialName("Q_platen_init_MW") val qPlatenInitMW: Double? = null,
    @SerialName("previous_run_id") val previousRunId: String? = null,
    val heating: Boolean = true,
    @SerialName("n_nodes") val nNodes: Int = 1,
    @SerialName("burner_schedule") val burnerSchedule: List<BurnerEventInput> = emptyList(),
    val preset: String? = null,
    @SerialName("q_platen_fraction") val qPlatenFraction: Double = 0.15,
    @SerialName("gas_to_metal_lag_s") val gasToMetalLagS: Double = 5.0,
    @SerialName("target_T_out_C") val targetTOutC: Double? = null,
    @SerialName("target_T_metal_C") val targetTMetalC: Double? = null,
)

// ---------------------------------------------------------------------------
// Responses (only the fields the UI consumes; unknown fields are ignored)
// ---------------------------------------------------------------------------

@Serializable
data class SteadyResponse(
    @SerialName("T_platen_in_C") val tPlatenInC: Double,
    @SerialName("T_platen_out_C") val tPlatenOutC: Double,
    @SerialName("deltaT_spray_C") val deltaTSprayC: Double,
    @SerialName("heat_absorbed_MW") val heatAbsorbedMW: Double,
    val Re: Double = 0.0,
    val Pr: Double = 0.0,
    val Nu: Double = 0.0,
    @SerialName("Nu_DB") val nuDb: Double = 0.0,
    @SerialName("Nu_Gnielinski") val nuGnielinski: Double = 0.0,
    @SerialName("h_W_m2K") val hWm2k: Double = 0.0,
    val regime: String = "",
    @SerialName("m_total_tph") val mTotalTph: Double = 0.0,
    @SerialName("h_main_kJ_kg") val hMainKjKg: Double = 0.0,
    @SerialName("h_spray_kJ_kg") val hSprayKjKg: Double = 0.0,
    @SerialName("h_mix_kJ_kg") val hMixKjKg: Double = 0.0,
    @SerialName("htc_method") val htcMethod: String = "",
    @SerialName("NTU") val ntu: Double = 0.0,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class InitialState(
    val mode: String = "",
    @SerialName("T_metal_C") val tMetalC: Double = 0.0,
    @SerialName("Q_platen_MW") val qPlatenMW: Double = 0.0,
    @SerialName("T_in_C") val tInC: Double = 0.0,
    @SerialName("T_out_C") val tOutC: Double = 0.0,
    @SerialName("T_mean_steam_C") val tMeanSteamC: Double = 0.0,
    @SerialName("h_W_m2K") val hWm2k: Double = 0.0,
    val Re: Double = 0.0,
    val Nu: Double = 0.0,
    val Pr: Double = 0.0,
    val regime: String = "",
    @SerialName("m_total_tph") val mTotalTph: Double = 0.0,
    @SerialName("P_bar") val pBar: Double = 0.0,
    @SerialName("initial_dTdt_C_per_s") val initialDTdtCPerS: Double = 0.0,
)

@Serializable
data class TransientResponse(
    @SerialName("time_s") val timeS: List<Double> = emptyList(),
    @SerialName("T_in_C") val tInC: List<Double> = emptyList(),
    @SerialName("T_out_C") val tOutC: List<Double> = emptyList(),
    @SerialName("T_metal_C") val tMetalC: List<Double> = emptyList(),
    @SerialName("Q_MW") val qMW: List<Double> = emptyList(),
    @SerialName("Q_gas_MW") val qGasMW: List<Double> = emptyList(),
    @SerialName("Q_steam_MW") val qSteamMW: List<Double> = emptyList(),
    @SerialName("Q_conv_MW") val qConvMW: List<Double> = emptyList(),
    val Re: List<Double> = emptyList(),
    val Pr: List<Double> = emptyList(),
    val Nu: List<Double> = emptyList(),
    @SerialName("h_W_m2K") val hWm2k: List<Double> = emptyList(),
    val regime: List<String> = emptyList(),
    @SerialName("tau_s") val tauS: Double = 0.0,
    @SerialName("t63_s") val t63S: Double? = null,
    @SerialName("t95_s") val t95S: Double? = null,
    @SerialName("duration_s") val durationS: Double = 0.0,
    @SerialName("dt_s") val dtS: Double = 0.0,
    @SerialName("n_steps") val nSteps: Int = 0,
    @SerialName("substeps_max") val substepsMax: Int = 1,
    val warnings: List<String> = emptyList(),
    @SerialName("initial_state") val initialState: InitialState? = null,
    @SerialName("initial_dTdt_C_per_s") val initialDTdtCPerS: Double = 0.0,
    @SerialName("m_total_tph") val mTotalTph: Double = 0.0,
    @SerialName("P_bar") val pBar: Double = 0.0,
    @SerialName("htc_method") val htcMethod: String = "",
    @SerialName("n_nodes") val nNodes: Int = 1,
)

@Serializable
data class BurnerEventOut(
    val tag: String = "",
    val level: String = "",
    val row: String = "",
    @SerialName("time_s") val timeS: Double = 0.0,
    val state: String = "",
    @SerialName("target_load_fraction") val targetLoadFraction: Double = 0.0,
    @SerialName("ramp_time_s") val rampTimeS: Double = 0.0,
)

@Serializable
data class BurnerStartupResponse(
    @SerialName("time_s") val timeS: List<Double> = emptyList(),
    @SerialName("T_out_C") val tOutC: List<Double> = emptyList(),
    @SerialName("T_metal_C") val tMetalC: List<Double> = emptyList(),
    @SerialName("T_in_C") val tInC: List<Double> = emptyList(),
    @SerialName("Q_MW") val qMW: List<Double> = emptyList(),
    @SerialName("Q_gas_MW") val qGasMW: List<Double> = emptyList(),
    val Re: List<Double> = emptyList(),
    val Nu: List<Double> = emptyList(),
    @SerialName("h_W_m2K") val hWm2k: List<Double> = emptyList(),
    val regime: List<String> = emptyList(),
    @SerialName("Q_burners_MW") val qBurnersMW: List<Double> = emptyList(),
    @SerialName("Q_gas_MW_platen") val qGasMWPlaten: List<Double> = emptyList(),
    @SerialName("burner_events") val burnerEvents: List<BurnerEventOut> = emptyList(),
    @SerialName("burner_states_final") val burnerStatesFinal: Map<String, Double> = emptyMap(),
    @SerialName("tau_s") val tauS: Double = 0.0,
    @SerialName("t63_s") val t63S: Double? = null,
    @SerialName("t95_s") val t95S: Double? = null,
    @SerialName("t_reach_T_out_s") val tReachTOutS: Double? = null,
    @SerialName("t_reach_T_metal_s") val tReachTMetalS: Double? = null,
    @SerialName("q_platen_fraction") val qPlatenFraction: Double = 0.15,
    @SerialName("gas_to_metal_lag_s") val gasToMetalLagS: Double = 5.0,
    val warnings: List<String> = emptyList(),
    @SerialName("initial_state") val initialState: InitialState? = null,
)

@Serializable
data class HtcResponse(
    val Re: Double = 0.0,
    val Pr: Double = 0.0,
    val Nu: Double = 0.0,
    @SerialName("Nu_DB") val nuDb: Double = 0.0,
    @SerialName("Nu_Gnielinski") val nuGnielinski: Double = 0.0,
    val f: Double = 0.0,
    @SerialName("h_W_m2K") val hWm2k: Double = 0.0,
    val regime: String = "",
    @SerialName("mu_Pas") val muPas: Double = 0.0,
    @SerialName("k_W_mK") val kWmK: Double = 0.0,
    @SerialName("cp_kJ_kgK") val cpKjKgK: Double = 0.0,
    @SerialName("m_dot_tube_tph") val mDotTubeTph: Double = 0.0,
    @SerialName("n_tubes") val nTubes: Int = 0,
    @SerialName("d_i_m") val dIM: Double = 0.0,
    val method: String = "",
)

@Serializable
data class PropertiesResponse(
    @SerialName("P_bar") val pBar: Double = 0.0,
    @SerialName("T_C") val tC: Double = 0.0,
    val region: Int? = null,
    val rho: Double = 0.0,
    val v: Double = 0.0,
    val h: Double = 0.0,
    val s: Double = 0.0,
    val cp: Double = 0.0,
    val mu: Double = 0.0,
    val k: Double = 0.0,
)

@Serializable
data class RunSummary(
    val id: String = "",
    @SerialName("created_at") val createdAt: String = "",
    val kind: String = "",
    val label: String = "",
    @SerialName("T_metal_C") val tMetalC: Double = 0.0,
    @SerialName("Q_platen_MW") val qPlatenMW: Double = 0.0,
    @SerialName("m_tph") val mTph: Double = 0.0,
    @SerialName("T_in_C") val tInC: Double = 0.0,
    @SerialName("T_out_C") val tOutC: Double = 0.0,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class RunDetail(
    val id: String = "",
    @SerialName("created_at") val createdAt: String = "",
    val kind: String = "",
    val label: String = "",
    @SerialName("T_metal_C") val tMetalC: Double = 0.0,
    @SerialName("Q_platen_MW") val qPlatenMW: Double = 0.0,
    @SerialName("m_tph") val mTph: Double = 0.0,
    @SerialName("T_in_C") val tInC: Double = 0.0,
    @SerialName("T_out_C") val tOutC: Double = 0.0,
    val warnings: List<String> = emptyList(),
    val payload: JsonObject = JsonObject(emptyMap()),
)

@Serializable
data class RunCreate(
    val kind: String,
    val label: String,
    @SerialName("T_metal_C") val tMetalC: Double,
    @SerialName("Q_platen_MW") val qPlatenMW: Double,
    @SerialName("m_tph") val mTph: Double,
    @SerialName("T_in_C") val tInC: Double,
    @SerialName("T_out_C") val tOutC: Double,
    val warnings: List<String> = emptyList(),
    val payload: JsonObject = JsonObject(emptyMap()),
)

@Serializable
data class BurnerSpec(
    val tag: String = "",
    val level: String = "",
    val row: String = "",
    val index: Int = 0,
    @SerialName("elevation_m") val elevationM: Double = 0.0,
    @SerialName("lateral_m") val lateralM: Double = 0.0,
    @SerialName("rated_MW") val ratedMW: Double = 40.0,
)

@Serializable
data class BurnerPreset(
    val id: String = "",
    @SerialName("event_count") val eventCount: Int = 0,
    @SerialName("label_en") val labelEn: String = "",
    @SerialName("label_fa") val labelFa: String = "",
)

@Serializable
data class HealthResponse(
    val status: String = "",
    val version: String = "",
    val if97: String = "",
)

@Serializable
data class ApiErrorDetail(
    val code: String = "error",
    @SerialName("message_en") val messageEn: String = "",
    @SerialName("message_fa") val messageFa: String = "",
)

@Serializable
data class ApiErrorEnvelope(val detail: ApiErrorDetail = ApiErrorDetail())
