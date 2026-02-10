package com.voxdocs.agent.scanner

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.voxdocs.agent.R
import com.voxdocs.agent.VoxDocsApp
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Full-screen camera activity that scans for a VoxDocs QR code.
 *
 * Expected QR format: voxdocs://{host}:{port}?token={jwt}
 *
 * On successful scan, saves settings and finishes with RESULT_OK.
 */
class QrScannerActivity : AppCompatActivity() {

    private lateinit var cameraExecutor: ExecutorService
    private var scanned = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_qr_scanner)

        cameraExecutor = Executors.newSingleThreadExecutor()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 100)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            Toast.makeText(this, "Camera permission required for QR scanning", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.surfaceProvider = findViewById<PreviewView>(R.id.preview_view).surfaceProvider
            }

            val scanner = BarcodeScanning.getClient()

            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                if (scanned) {
                    imageProxy.close()
                    return@setAnalyzer
                }

                val mediaImage = imageProxy.image
                if (mediaImage != null) {
                    val inputImage = InputImage.fromMediaImage(
                        mediaImage, imageProxy.imageInfo.rotationDegrees
                    )

                    scanner.process(inputImage)
                        .addOnSuccessListener { barcodes ->
                            for (barcode in barcodes) {
                                if (barcode.valueType == Barcode.TYPE_TEXT ||
                                    barcode.valueType == Barcode.TYPE_URL
                                ) {
                                    val raw = barcode.rawValue ?: continue
                                    if (raw.startsWith("voxdocs://")) {
                                        scanned = true
                                        handleQrPayload(raw)
                                        return@addOnSuccessListener
                                    }
                                }
                            }
                        }
                        .addOnCompleteListener {
                            imageProxy.close()
                        }
                } else {
                    imageProxy.close()
                }
            }

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageAnalysis
                )
            } catch (e: Exception) {
                Log.e(TAG, "Camera bind failed", e)
            }

        }, ContextCompat.getMainExecutor(this))
    }

    private fun handleQrPayload(raw: String) {
        // Parse: voxdocs://host:port?token=JWT
        try {
            val uri = Uri.parse(raw)
            val host = uri.host ?: ""
            val port = uri.port.let { if (it > 0) ":$it" else "" }
            val token = uri.getQueryParameter("token") ?: ""

            val serverUrl = "http://$host$port"

            val settings = VoxDocsApp.instance.settings
            settings.serverUrl = serverUrl
            settings.authToken = token

            Log.i(TAG, "QR config applied: $serverUrl")

            runOnUiThread {
                Toast.makeText(
                    this,
                    "✅ Configured: $serverUrl",
                    Toast.LENGTH_LONG
                ).show()
                setResult(RESULT_OK)
                finish()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse QR", e)
            runOnUiThread {
                Toast.makeText(this, "Invalid QR code", Toast.LENGTH_SHORT).show()
                scanned = false // allow retry
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }

    companion object {
        private const val TAG = "QrScanner"
    }
}
