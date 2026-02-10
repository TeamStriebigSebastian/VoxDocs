package com.voxdocs.agent

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings as AndroidSettings
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.android.material.button.MaterialButton
import com.google.android.material.switchmaterial.SwitchMaterial
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textview.MaterialTextView
import com.voxdocs.agent.scanner.QrScannerActivity
import com.voxdocs.agent.service.VoiceListenerService

/**
 * Minimal settings screen.
 * Lets the user configure the backend URL, auth token, and toggle listening.
 * Supports QR code scanning for quick setup.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var etServerUrl: TextInputEditText
    private lateinit var etAuthToken: TextInputEditText
    private lateinit var switchListening: SwitchMaterial
    private lateinit var switchAutoStart: SwitchMaterial
    private lateinit var tvStatus: MaterialTextView
    private lateinit var btnSave: MaterialButton
    private lateinit var btnBattery: MaterialButton
    private lateinit var btnScanQr: MaterialButton

    private val settings by lazy { VoxDocsApp.instance.settings }

    // QR scanner result handler
    private val qrScanLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            // Settings were updated by QrScannerActivity — reload UI
            etServerUrl.setText(settings.serverUrl)
            etAuthToken.setText(settings.authToken)
            updateStatus()
            Toast.makeText(this, "✅ Configuration imported from QR code!", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etServerUrl     = findViewById(R.id.et_server_url)
        etAuthToken     = findViewById(R.id.et_auth_token)
        switchListening = findViewById(R.id.switch_listening)
        switchAutoStart = findViewById(R.id.switch_auto_start)
        tvStatus        = findViewById(R.id.tv_status)
        btnSave         = findViewById(R.id.btn_save)
        btnBattery      = findViewById(R.id.btn_battery)
        btnScanQr       = findViewById(R.id.btn_scan_qr)

        // Load current settings
        etServerUrl.setText(settings.serverUrl)
        etAuthToken.setText(settings.authToken)
        switchListening.isChecked = settings.listeningEnabled
        switchAutoStart.isChecked = settings.autoStartOnBoot

        btnSave.setOnClickListener { saveSettings() }
        btnBattery.setOnClickListener { requestBatteryExclusion() }
        btnScanQr.setOnClickListener { launchQrScanner() }

        switchListening.setOnCheckedChangeListener { _, isChecked ->
            settings.listeningEnabled = isChecked
            if (isChecked) startListening() else stopListening()
        }

        switchAutoStart.setOnCheckedChangeListener { _, isChecked ->
            settings.autoStartOnBoot = isChecked
        }

        requestPermissions()
        updateStatus()
    }

    override fun onResume() {
        super.onResume()
        // Refresh fields in case QR scanner updated them
        etServerUrl.setText(settings.serverUrl)
        etAuthToken.setText(settings.authToken)
        updateStatus()
    }

    private fun saveSettings() {
        settings.serverUrl = etServerUrl.text?.toString()?.trim() ?: ""
        settings.authToken = etAuthToken.text?.toString()?.trim() ?: ""
        Toast.makeText(this, "Settings saved", Toast.LENGTH_SHORT).show()
        updateStatus()
    }

    private fun launchQrScanner() {
        qrScanLauncher.launch(Intent(this, QrScannerActivity::class.java))
    }

    private fun startListening() {
        if (!settings.isConfigured) {
            Toast.makeText(this, "Configure server URL and token first", Toast.LENGTH_LONG).show()
            switchListening.isChecked = false
            settings.listeningEnabled = false
            return
        }
        val intent = Intent(this, VoiceListenerService::class.java)
        ContextCompat.startForegroundService(this, intent)
        updateStatus()
    }

    private fun stopListening() {
        stopService(Intent(this, VoiceListenerService::class.java))
        updateStatus()
    }

    private fun updateStatus() {
        val configured = settings.isConfigured
        val listening = settings.listeningEnabled
        val status = when {
            !configured -> "⚙️  Configure server URL and auth token"
            listening   -> "🎤  Listening for \"Hey VoxDocs\"…"
            else        -> "⏸️  Ready — enable listening to start"
        }
        tvStatus.text = status
    }

    // ── Permissions ─────────────────────────────────────────────────

    private fun requestPermissions() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECORD_AUDIO)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.BLUETOOTH_CONNECT)
            }
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), RC_PERMS)
        }
    }

    private fun requestBatteryExclusion() {
        val pm = getSystemService(PowerManager::class.java)
        if (!pm.isIgnoringBatteryOptimizations(packageName)) {
            val intent = Intent(AndroidSettings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        } else {
            Toast.makeText(this, "Battery optimization already disabled", Toast.LENGTH_SHORT).show()
        }
    }

    companion object {
        private const val RC_PERMS = 100
    }
}
