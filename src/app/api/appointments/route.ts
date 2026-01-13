import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { saveFile } from '@/lib/storage';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();

    const startTime = formData.get('startTime') as string;
    const patientName = formData.get('patientName') as string;

    const appointment = await prisma.appointment.create({
      data: {
        startTime: new Date(startTime),
        patientName: patientName || 'Unbekannt',
        status: 'IN_PROGRESS',
      },
    });

    const audioFiles: string[] = [];
    const photoFiles: string[] = [];

    for (const [key, value] of formData.entries()) {
      if (key.startsWith('audio-') && value instanceof File) {
        const buffer = Buffer.from(await value.arrayBuffer());
        const filename = `${appointment.id}-${Date.now()}-${key}.webm`;
        const fileUrl = await saveFile(buffer, filename, 'audio');

        await prisma.audioRecording.create({
          data: {
            appointmentId: appointment.id,
            fileUrl,
            fileName: filename,
            mimeType: value.type,
            fileSize: value.size,
          },
        });

        audioFiles.push(fileUrl);
      } else if (key.startsWith('photo-') && value instanceof File) {
        const buffer = Buffer.from(await value.arrayBuffer());
        const filename = `${appointment.id}-${Date.now()}-${key}.jpg`;
        const fileUrl = await saveFile(buffer, filename, 'photos');

        await prisma.photo.create({
          data: {
            appointmentId: appointment.id,
            fileUrl,
            fileName: filename,
            mimeType: value.type,
            fileSize: value.size,
          },
        });

        photoFiles.push(fileUrl);
      }
    }

    await prisma.appointment.update({
      where: { id: appointment.id },
      data: {
        endTime: new Date(),
        status: 'COMPLETED',
      },
    });

    triggerTranscription(appointment.id);

    return NextResponse.json({
      id: appointment.id,
      audioFiles,
      photoFiles,
      message: 'Termin erfolgreich erstellt',
    });
  } catch (error) {
    console.error('Error creating appointment:', error);
    return NextResponse.json(
      { error: 'Fehler beim Erstellen des Termins' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const appointments = await prisma.appointment.findMany({
      include: {
        audioRecordings: true,
        photos: true,
        transcription: true,
      },
      orderBy: {
        startTime: 'desc',
      },
    });

    return NextResponse.json(appointments);
  } catch (error) {
    console.error('Error fetching appointments:', error);
    return NextResponse.json(
      { error: 'Fehler beim Abrufen der Termine' },
      { status: 500 }
    );
  }
}

async function triggerTranscription(appointmentId: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';

    fetch(`${baseUrl}/api/transcribe`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ appointmentId }),
    }).catch(err => {
      console.error('Error triggering transcription:', err);
    });
  } catch (error) {
    console.error('Error in triggerTranscription:', error);
  }
}
