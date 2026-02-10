package com.voxdocs.agent.api

import org.json.JSONArray
import org.json.JSONObject

// ── Data classes shared across the app ──────────────────────────────

/** A case file from the backend. */
data class CaseInfo(
    val id: String,     // UUID
    val name: String,   // Display name, e.g. "Demian"
)

/** A single task belonging to a case. */
data class TaskInfo(
    val id: String,
    val title: String,
    val status: String,
)

/** Response from POST /api/voice/intake for CREATE intent. */
data class IntakeCreateResponse(
    val caseId: String,
    val noteId: String?,
    val createdTasks: List<TaskInfo>,
)

/** Response from GET /api/cases/{uuid}/tasks. */
data class TaskListResponse(
    val tasks: List<TaskInfo>,
)

// ── Intent models (local) ───────────────────────────────────────────

enum class VoiceIntentType {
    CREATE_TASK_OR_NOTE,
    READ_OPEN_TASKS,
    UNKNOWN,
}

/**
 * Result of local intent parsing from the SpeechRecognizer transcript.
 *
 * @param type       The classified intent
 * @param caseName   Spoken case name (null if implicit / not detected)
 * @param rawText    The original transcript
 */
data class VoiceIntent(
    val type: VoiceIntentType,
    val caseName: String?,
    val rawText: String,
)

/** Metadata attached to every audio upload. */
data class IntakeMeta(
    val deviceId: String,
    val locale: String,
    val capturedAt: String,     // ISO-8601
    val caseName: String,
    val caseId: String?,
    val intent: String,         // "CREATE" | "READ_TASKS"
    val source: String,         // "headset" | "phone"
    val clientVersion: String,
) {
    fun toJson(): String = JSONObject().apply {
        put("deviceId", deviceId)
        put("locale", locale)
        put("capturedAt", capturedAt)
        put("caseName", caseName)
        if (caseId != null) put("caseId", caseId)
        put("intent", intent)
        put("source", source)
        put("clientVersion", clientVersion)
    }.toString()
}

// ── Case-match result ───────────────────────────────────────────────

sealed class CaseMatchResult {
    data class Exact(val case: CaseInfo) : CaseMatchResult()
    data class Fuzzy(val case: CaseInfo, val score: Int) : CaseMatchResult()
    data class Ambiguous(val candidates: List<CaseInfo>) : CaseMatchResult()
    object NoMatch : CaseMatchResult()
}

// ── JSON parsing helpers ────────────────────────────────────────────

fun JSONObject.toCaseInfo() = CaseInfo(
    id   = optString("uuid", optString("id", "")),
    name = optString("title", optString("name", "")),
)

fun JSONArray.toCaseList(): List<CaseInfo> =
    (0 until length()).map { getJSONObject(it).toCaseInfo() }

fun JSONObject.toTaskInfo() = TaskInfo(
    id     = optString("uuid", optString("id", "")),
    title  = optString("title", ""),
    status = optString("status", "open"),
)

fun JSONArray.toTaskList(): List<TaskInfo> =
    (0 until length()).map { getJSONObject(it).toTaskInfo() }
