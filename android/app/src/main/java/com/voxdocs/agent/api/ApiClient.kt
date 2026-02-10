package com.voxdocs.agent.api

import android.util.Log
import com.voxdocs.agent.data.SettingsStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * OkHttp-based API client for the VoxDocs backend.
 *
 * All methods are suspend functions safe to call from coroutines.
 */
class ApiClient(private val settings: SettingsStore) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)   // large uploads
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val baseUrl: String get() = settings.serverUrl
    private val token: String get() = settings.authToken

    // ── Upload audio command ────────────────────────────────────────

    /**
     * POST /api/voice/intake
     *
     * Uploads the recorded audio + metadata for backend processing.
     * Returns the parsed response or throws on failure.
     */
    suspend fun uploadVoiceCommand(
        audioFile: File,
        meta: IntakeMeta,
    ): IntakeCreateResponse = withContext(Dispatchers.IO) {
        val body = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart(
                "audio", audioFile.name,
                audioFile.asRequestBody("audio/wav".toMediaType())
            )
            .addFormDataPart("meta", meta.toJson())
            .build()

        val request = Request.Builder()
            .url("$baseUrl/api/voice/intake")
            .addHeader("Authorization", "Bearer $token")
            .post(body)
            .build()

        val responseBody = executeRequest(request)
        val json = JSONObject(responseBody)

        IntakeCreateResponse(
            caseId = json.optString("caseId", ""),
            noteId = json.optString("noteId", null),
            createdTasks = json.optJSONArray("createdTasks")?.toTaskList() ?: emptyList(),
        )
    }

    // ── Fetch cases ─────────────────────────────────────────────────

    /**
     * GET /api/cases/?group_id={groupId}
     *
     * Fetches the list of cases for caching and fuzzy matching.
     */
    suspend fun fetchCases(groupId: Int = 1): List<CaseInfo> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$baseUrl/api/cases/?group_id=$groupId")
            .addHeader("Authorization", "Bearer $token")
            .get()
            .build()

        val responseBody = executeRequest(request)
        val arr = JSONArray(responseBody)
        arr.toCaseList()
    }

    // ── Fetch open tasks for a case ─────────────────────────────────

    /**
     * GET /api/tasks/?case_uuid={caseUuid}&status=open
     */
    suspend fun fetchOpenTasks(caseUuid: String): List<TaskInfo> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$baseUrl/api/tasks/?case_uuid=$caseUuid&status=open")
            .addHeader("Authorization", "Bearer $token")
            .get()
            .build()

        val responseBody = executeRequest(request)
        // The API might return a JSON array or an object with a "tasks" key
        try {
            val arr = JSONArray(responseBody)
            arr.toTaskList()
        } catch (e: Exception) {
            val obj = JSONObject(responseBody)
            obj.optJSONArray("tasks")?.toTaskList() ?: emptyList()
        }
    }

    // ── Internals ───────────────────────────────────────────────────

    private suspend fun executeRequest(request: Request): String =
        suspendCancellableCoroutine { cont ->
            val call = client.newCall(request)
            cont.invokeOnCancellation { call.cancel() }

            call.enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    if (cont.isActive) cont.resumeWithException(e)
                }

                override fun onResponse(call: Call, response: Response) {
                    response.use {
                        val body = it.body?.string() ?: ""
                        if (!it.isSuccessful) {
                            val msg = "HTTP ${it.code}: $body"
                            Log.e(TAG, msg)
                            if (cont.isActive) cont.resumeWithException(IOException(msg))
                        } else {
                            if (cont.isActive) cont.resume(body)
                        }
                    }
                }
            })
        }

    companion object {
        private const val TAG = "ApiClient"
    }
}
