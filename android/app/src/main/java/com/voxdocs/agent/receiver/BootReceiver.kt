package com.voxdocs.agent.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.ContextCompat
import com.voxdocs.agent.VoxDocsApp
import com.voxdocs.agent.service.VoiceListenerService

/**
 * Starts the voice listener service on device boot if the user has opted in.
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return

        val settings = VoxDocsApp.instance.settings
        if (settings.autoStartOnBoot && settings.isConfigured) {
            Log.i("BootReceiver", "Auto-starting voice listener after boot")
            val serviceIntent = Intent(context, VoiceListenerService::class.java)
            ContextCompat.startForegroundService(context, serviceIntent)
        }
    }
}
