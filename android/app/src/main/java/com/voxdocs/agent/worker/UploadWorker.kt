package com.voxdocs.agent.worker

import android.content.Context
import android.util.Log
import androidx.work.*
import com.voxdocs.agent.VoxDocsApp
import com.voxdocs.agent.api.ApiClient
import com.voxdocs.agent.api.IntakeMeta
import com.voxdocs.agent.data.OfflineQueue
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * WorkManager worker that retries failed audio uploads from the [OfflineQueue].
 *
 * Scheduled with exponential backoff. Processes all queued items sequentially.
 */
class UploadWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val settings = VoxDocsApp.instance.settings
        val apiClient = ApiClient(settings)
        val queue = OfflineQueue(applicationContext)

        val pending = queue.listPending()
        if (pending.isEmpty()) {
            Log.i(TAG, "No pending uploads")
            return@withContext Result.success()
        }

        Log.i(TAG, "Processing ${pending.size} queued uploads")
        var failures = 0

        for (item in pending) {
            try {
                val metaObj = JSONObject(item.metaJson)
                val meta = IntakeMeta(
                    deviceId = metaObj.optString("deviceId", ""),
                    locale = metaObj.optString("locale", "de-DE"),
                    capturedAt = metaObj.optString("capturedAt", ""),
                    caseName = metaObj.optString("caseName", ""),
                    caseId = metaObj.optString("caseId", null),
                    intent = metaObj.optString("intent", "CREATE"),
                    source = metaObj.optString("source", "phone"),
                    clientVersion = metaObj.optString("clientVersion", "0.1.0"),
                )

                apiClient.uploadVoiceCommand(item.audioFile, meta)
                queue.remove(item)
                Log.i(TAG, "Uploaded queued item: ${item.audioFile.name}")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to upload ${item.audioFile.name}", e)
                failures++
            }
        }

        if (failures > 0) Result.retry() else Result.success()
    }

    companion object {
        private const val TAG = "UploadWorker"
        private const val WORK_NAME = "voxdocs_upload_retry"

        /** Enqueue a one-time upload retry with backoff. */
        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = OneTimeWorkRequestBuilder<UploadWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30, TimeUnit.SECONDS
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(WORK_NAME, ExistingWorkPolicy.REPLACE, request)

            Log.i(TAG, "Upload retry worker enqueued")
        }
    }
}
