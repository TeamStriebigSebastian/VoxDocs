"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import AudioRecorder from "@/components/AudioRecorder";
import CameraCapture from "@/components/CameraCapture";
import { FaTrash, FaPlay, FaPause, FaCheck, FaArrowLeft } from "react-icons/fa";
import Link from "next/link";

interface AudioRecording {
  id: string;
  blob: Blob;
  url: string;
  duration: number;
  createdAt: Date;
}

interface Photo {
  id: string;
  blob: Blob;
  url: string;
  createdAt: Date;
}

export default function NewAppointmentPage() {
  const router = useRouter();
  const [audioRecordings, setAudioRecordings] = useState<AudioRecording[]>([]);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRecordingComplete = (recording: AudioRecording) => {
    setAudioRecordings(prev => [...prev, recording]);
  };

  const handlePhotoCapture = (photo: Photo) => {
    setPhotos(prev => [...prev, photo]);
  };

  const deleteAudio = (id: string) => {
    setAudioRecordings(prev => {
      const recording = prev.find(r => r.id === id);
      if (recording) {
        URL.revokeObjectURL(recording.url);
      }
      return prev.filter(r => r.id !== id);
    });
  };

  const deletePhoto = (id: string) => {
    setPhotos(prev => {
      const photo = prev.find(p => p.id === id);
      if (photo) {
        URL.revokeObjectURL(photo.url);
      }
      return prev.filter(p => p.id !== id);
    });
  };

  const toggleAudioPlayback = (id: string) => {
    if (playingAudioId === id) {
      setPlayingAudioId(null);
    } else {
      setPlayingAudioId(id);
    }
  };

  const submitAppointment = async () => {
    if (audioRecordings.length === 0) {
      alert('Bitte mindestens eine Audio-Aufnahme erstellen.');
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();

      formData.append('startTime', new Date().toISOString());
      formData.append('patientName', 'Patient'); // Könnte erweitert werden

      audioRecordings.forEach((recording, index) => {
        formData.append(`audio-${index}`, recording.blob, `recording-${index}.webm`);
      });

      photos.forEach((photo, index) => {
        formData.append(`photo-${index}`, photo.blob, `photo-${index}.jpg`);
      });

      const response = await fetch('/api/appointments', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Fehler beim Erstellen des Termins');
      }

      const data = await response.json();

      alert('Termin erfolgreich erstellt! Die Transkription wird verarbeitet...');
      router.push(`/appointment/${data.id}`);
    } catch (error) {
      console.error('Fehler beim Erstellen des Termins:', error);
      alert('Fehler beim Erstellen des Termins. Bitte versuchen Sie es erneut.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto pb-32">
      <header className="mb-8 pt-8">
        <Link href="/" className="inline-flex items-center gap-2 text-primary-600 hover:text-primary-700 mb-4">
          <FaArrowLeft />
          Zurück
        </Link>
        <h1 className="text-4xl font-bold text-primary-600 mb-2">
          Neuer Termin
        </h1>
        <p className="text-gray-600">
          Erstelle Audio-Aufnahmen und Fotos für den Pflegetermin
        </p>
      </header>

      <div className="space-y-6">
        <AudioRecorder onRecordingComplete={handleRecordingComplete} />

        {audioRecordings.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-lg mb-4">
              Audio-Aufnahmen ({audioRecordings.length})
            </h3>
            <div className="space-y-3">
              {audioRecordings.map((recording) => (
                <div
                  key={recording.id}
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                >
                  <button
                    onClick={() => toggleAudioPlayback(recording.id)}
                    className="p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    {playingAudioId === recording.id ? <FaPause size={16} /> : <FaPlay size={16} />}
                  </button>
                  <div className="flex-1">
                    <p className="font-medium">
                      Aufnahme {audioRecordings.indexOf(recording) + 1}
                    </p>
                    <p className="text-sm text-gray-600">
                      {formatDuration(recording.duration)} • {recording.createdAt.toLocaleTimeString('de-DE')}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteAudio(recording.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <FaTrash />
                  </button>

                  {playingAudioId === recording.id && (
                    <audio
                      src={recording.url}
                      autoPlay
                      onEnded={() => setPlayingAudioId(null)}
                      className="hidden"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <CameraCapture onPhotoCapture={handlePhotoCapture} />

        {photos.length > 0 && (
          <div className="card">
            <h3 className="font-semibold text-lg mb-4">
              Fotos ({photos.length})
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {photos.map((photo) => (
                <div key={photo.id} className="relative group">
                  <img
                    src={photo.url}
                    alt={`Foto ${photos.indexOf(photo) + 1}`}
                    className="w-full h-48 object-cover rounded-lg"
                  />
                  <button
                    onClick={() => deletePhoto(photo.id)}
                    className="absolute top-2 right-2 p-2 bg-red-600 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <FaTrash size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {(audioRecordings.length > 0 || photos.length > 0) && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg">
          <div className="max-w-4xl mx-auto">
            <button
              onClick={submitAppointment}
              disabled={isSubmitting || audioRecordings.length === 0}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FaCheck />
              {isSubmitting ? 'Wird hochgeladen...' : 'Termin abschließen'}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
