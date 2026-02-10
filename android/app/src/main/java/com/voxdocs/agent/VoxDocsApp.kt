package com.voxdocs.agent

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.voxdocs.agent.data.SettingsStore

/**
 * Application class — initialises singletons and notification channels.
 */
class VoxDocsApp : Application() {

    lateinit var settings: SettingsStore
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        settings = SettingsStore(this)
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        val channel = NotificationChannel(
            CHANNEL_LISTENER,
            "Voice Listener",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Persistent notification while listening for wakeword"
            setShowBadge(false)
        }

        val alertChannel = NotificationChannel(
            CHANNEL_ALERTS,
            "Alerts",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Voice command results and errors"
        }

        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(channel)
        nm.createNotificationChannel(alertChannel)
    }

    companion object {
        const val CHANNEL_LISTENER = "voice_listener"
        const val CHANNEL_ALERTS  = "voice_alerts"

        lateinit var instance: VoxDocsApp
            private set
    }
}
