"use client";

import { useState, useRef } from "react";
import { FaCamera, FaTimes, FaCheck } from "react-icons/fa";

interface Photo {
  id: string;
  blob: Blob;
  url: string;
  createdAt: Date;
}

interface CameraCaptureProps {
  onPhotoCapture: (photo: Photo) => void;
}

export default function CameraCapture({ onPhotoCapture }: CameraCaptureProps) {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const openCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, // Rückkamera bevorzugen
        audio: false,
      });

      setStream(mediaStream);
      setIsCameraOpen(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (error) {
      console.error('Fehler beim Zugriff auf die Kamera:', error);
      alert('Fehler beim Zugriff auf die Kamera. Bitte Berechtigungen prüfen.');
    }
  };

  const closeCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setIsCameraOpen(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    if (!context) return;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (!blob) return;

      const photo: Photo = {
        id: `photo-${Date.now()}`,
        blob,
        url: URL.createObjectURL(blob),
        createdAt: new Date(),
      };

      onPhotoCapture(photo);
      closeCamera();
    }, 'image/jpeg', 0.95);
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="bg-primary-100 text-primary-600 p-3 rounded-full">
            <FaCamera size={24} />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Foto aufnehmen</h3>
            <p className="text-gray-600 text-sm">
              Dokumentiere visuelle Befunde
            </p>
          </div>
        </div>
      </div>

      {!isCameraOpen ? (
        <button
          onClick={openCamera}
          className="btn-primary flex items-center gap-2 w-full"
        >
          <FaCamera />
          Kamera öffnen
        </button>
      ) : (
        <div className="space-y-4">
          <div className="relative bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="w-full h-auto"
            />
          </div>

          <canvas ref={canvasRef} className="hidden" />

          <div className="flex gap-3">
            <button
              onClick={closeCamera}
              className="btn-secondary flex items-center gap-2 flex-1"
            >
              <FaTimes />
              Abbrechen
            </button>
            <button
              onClick={capturePhoto}
              className="btn-primary flex items-center gap-2 flex-1"
            >
              <FaCheck />
              Foto aufnehmen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
