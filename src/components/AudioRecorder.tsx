"use client";

import { useState, useRef, useEffect } from "react";
import { FaPlay, FaStop, FaMicrophone } from "react-icons/fa";

interface AudioRecording {
  id: string;
  blob: Blob;
  url: string;
  duration: number;
  createdAt: Date;
}

interface AudioRecorderProps {
  onRecordingComplete: (recording: AudioRecording) => void;
}

export default function AudioRecorder({ onRecordingComplete }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);
  const pausedTimeRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, [isRecording]);

  const startTimer = () => {
    startTimeRef.current = Date.now() - pausedTimeRef.current;
    timerRef.current = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current;
      setRecordingTime(Math.floor(elapsed / 1000));
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm;codecs=opus' });
        const url = URL.createObjectURL(blob);

        const recording: AudioRecording = {
          id: `recording-${Date.now()}`,
          blob,
          url,
          duration: recordingTime,
          createdAt: new Date(),
        };

        onRecordingComplete(recording);

        stream.getTracks().forEach(track => track.stop());

        setRecordingTime(0);
        pausedTimeRef.current = 0;
        chunksRef.current = [];
      };

      mediaRecorder.start();
      setIsRecording(true);
      setIsPaused(false);
      startTimer();
    } catch (error) {
      console.error('Fehler beim Zugriff auf das Mikrofon:', error);
      alert('Fehler beim Zugriff auf das Mikrofon. Bitte Berechtigungen prüfen.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
      stopTimer();
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume();
        startTimer();
        setIsPaused(false);
      } else {
        mediaRecorderRef.current.pause();
        stopTimer();
        pausedTimeRef.current = recordingTime * 1000;
        setIsPaused(true);
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-full ${isRecording ? 'bg-red-100 animate-pulse' : 'bg-gray-100'}`}>
            <FaMicrophone className={isRecording ? 'text-red-600' : 'text-gray-600'} size={24} />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Audio-Aufnahme</h3>
            <p className="text-gray-600 text-sm">
              {isRecording ? (isPaused ? 'Pausiert' : 'Aufnahme läuft...') : 'Bereit zur Aufnahme'}
            </p>
          </div>
        </div>

        {isRecording && (
          <div className="text-2xl font-mono font-bold text-red-600">
            {formatTime(recordingTime)}
          </div>
        )}
      </div>

      <div className="flex gap-3">
        {!isRecording ? (
          <button
            onClick={startRecording}
            className="btn-primary flex items-center gap-2 flex-1"
          >
            <FaPlay />
            Aufnahme starten
          </button>
        ) : (
          <>
            <button
              onClick={pauseRecording}
              className="btn-secondary flex items-center gap-2 flex-1"
            >
              {isPaused ? <FaPlay /> : <FaStop />}
              {isPaused ? 'Fortsetzen' : 'Pausieren'}
            </button>
            <button
              onClick={stopRecording}
              className="btn-danger flex items-center gap-2 flex-1"
            >
              <FaStop />
              Beenden
            </button>
          </>
        )}
      </div>
    </div>
  );
}
